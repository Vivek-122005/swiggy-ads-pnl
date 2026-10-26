"""Run the ads-marketplace simulation and write raw tables.

    python -m simulator.run --config config/sim_config.yaml --out data/raw

ALL DATA IS SIMULATED. Real restaurant names (if the Kaggle file is present) are used for
realism only; every ad metric attached to them is invented.
"""
from __future__ import annotations

import argparse
import gc
import gzip
import io
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from simulator import anomalies as anom
from simulator.auction import gsp, pacing_throttle
from simulator.behaviour import cvr, fatigue, hour_ctr_factor, order_delays_seconds, order_values, true_ctr
from simulator.entities import build_advertisers, build_campaigns, build_zones
from simulator.lifecycle import weekly_update
from simulator.traffic import Calendar, day_sessions

SURFACES = ["food_listing", "instamart_search", "home_banner"]
PLATFORMS = ["android", "ios"]
USERS_PER_ZONE = 400_000
BOT_USERS = 40
PLATFORM_CONV = {"food": 0.18, "instamart": 0.20}
PLATFORM_AOV = {"food": 430.0, "instamart": 540.0}


def load_config(path: str | Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


class Simulator:
    def __init__(self, cfg: dict, external_dir: Path | None = None, weeks: int | None = None):
        self.cfg = cfg
        if weeks:
            cfg["calendar"]["weeks"] = weeks
        self.rng = np.random.default_rng(cfg["seed"])
        rng = self.rng
        self.zones = build_zones(cfg)
        self.nz = len(self.zones)
        self.adv = build_advertisers(cfg, self.zones, rng, external_dir)
        self.camps = build_campaigns(cfg, self.adv, self.zones, rng)
        self.cal = Calendar(cfg, rng)
        self.paused_brand = anom.pick_paused_brand(self.adv, self.camps)
        self.camps_initial = self.camps.copy()

        adv_pos = {a: i for i, a in enumerate(self.adv["advertiser_id"])}
        c = self.camps
        c["_adv_idx"] = c["advertiser_id"].map(adv_pos).astype(int)
        self.c_adv = c["_adv_idx"].to_numpy()
        self.c_surface = c["product"].map({s: i for i, s in enumerate(SURFACES)}).to_numpy()
        zid = {z: i for i, z in enumerate(self.zones["zone_id"])}
        self.c_zone = np.zeros((len(c), self.nz), bool)
        for i, tz in enumerate(c["target_zones"]):
            for z in tz.split("|"):
                self.c_zone[i, zid[z]] = True
        cats = [x["category"] for x in cfg["instamart_categories"]]
        self.cats = cats
        self.cat_w = np.array([x["weight"] for x in cfg["instamart_categories"]], float)
        self.cat_w /= self.cat_w.sum()
        self.c_cat = c["category"].map({k: i for i, k in enumerate(cats)}).fillna(-1).astype(int).to_numpy().copy()
        # the A2 brand runs a multi-category portfolio (snacks, beverages, frozen...): eligible in every category
        self.c_cat[((c["advertiser_id"] == self.paused_brand) & (c["product"] == "instamart_search")).to_numpy()] = -2
        day0 = pd.Timestamp(cfg["calendar"]["start_date"])
        self.c_start = (pd.to_datetime(c["start_date"]) - day0).dt.days.to_numpy()
        self.c_end = (pd.to_datetime(c["end_date"]) - day0).dt.days.to_numpy()
        self.quality = self.adv["true_quality"].to_numpy()[self.c_adv]
        self.rating = self.adv["rating"].to_numpy()[self.c_adv]
        self.price_ref = self.adv["cost_for_two"].to_numpy()[self.c_adv]
        self.c_open = self._opening_hours(rng)
        # Bigger accounts reach more requests (multi-outlet chains, broad keyword sets) -> concentration
        base_e = np.array([cfg["surfaces"][s_]["eligibility"] for s_ in SURFACES])[self.c_surface]
        bud = c["daily_budget"].to_numpy()
        rel = np.ones(len(c))
        for si in range(3):
            m = self.c_surface == si
            rel[m] = bud[m] / np.median(bud[m])
        self.p_elig = np.clip(base_e * np.clip(rel, 0.4, 40.0) ** 0.6, 0.0, 0.95)
        # the A2 brand is a top-3 Instamart spender: broad keyword coverage on its category
        self.p_elig[(c["advertiser_id"] == self.paused_brand).to_numpy() & (self.c_surface == 1)] = 0.45
        self.churned = np.zeros(len(self.adv), bool)
        self.prev_imps = np.zeros(len(c))
        self.paused_mask = (c["advertiser_id"] == self.paused_brand).to_numpy()
        self.lifecycle_log: list[dict] = []
        self.out: dict[str, list[pd.DataFrame]] = {k: [] for k in
            ["ad_requests", "impressions", "clicks", "orders", "billing", "budget_daily", "platform_daily"]}
        self.week_spend: dict[int, np.ndarray] = {}
        self.week_gmv: dict[int, np.ndarray] = {}
        self._click_seq = 0
        self._order_seq = 0

    # ------------------------------------------------------------------ helpers
    def _opening_hours(self, rng) -> np.ndarray:
        """[campaign, hour] bool. Restaurants keep kitchen hours; brands are always on."""
        n = len(self.camps)
        open_ = np.ones((n, 24), bool)
        cuisine = self.adv["cuisine"].to_numpy()[self.c_adv]
        is_rest = self.c_surface == 0
        breakfast = np.isin(cuisine, ["south_indian", "cafe", "bakery"])
        latenight_c = np.isin(cuisine, ["biryani", "rolls", "burger", "pizza", "street_food", "chinese"])
        opens = np.where(breakfast, rng.integers(6, 9, n), rng.integers(10, 12, n))
        closes = np.where(latenight_c & (rng.random(n) < 0.35), rng.integers(25, 28, n), rng.integers(22, 24, n))  # 25 = 1am
        for h in range(24):
            hh = np.where(h < 6, h + 24, h)
            open_[:, h] = ~is_rest | ((opens <= hh) & (hh < closes))
        return open_

    def _cum_share(self, vertical: str) -> np.ndarray:
        curve = np.asarray(self.cfg["traffic"][f"{vertical}_hour_curve"], float)
        curve = curve / curve.sum()
        return np.concatenate([[0.0], np.cumsum(curve)[:-1]])

    def _active(self, di: int, d: pd.Timestamp) -> np.ndarray:
        act = (self.c_start <= di) & (di <= self.c_end) & ~self.churned[self.c_adv]
        if self.cal.in_anomaly("A2", d):
            act &= ~self.paused_mask
        return act

    # ------------------------------------------------------------------ one day
    def simulate_day(self, di: int, d: pd.Timestamp):
        cfg, rng = self.cfg, self.rng
        S = cfg["surfaces"]
        sess = day_sessions(cfg, self.cal, d, self.zones, rng)
        active = self._active(di, d)
        budget = self.camps["daily_budget"].to_numpy().copy()
        bids = self.camps["bid"].to_numpy().copy()
        if self.cal.in_anomaly("A7", d):
            bids = bids * self.cal.anomaly("A7")["bid_boost"]
        spent = np.zeros(len(budget))
        fat = fatigue(self.prev_imps, cfg["behaviour"]["fatigue_strength"])
        imps_today = np.zeros(len(budget))
        banner_reserve = S["home_banner"]["reserve"] * (self.cal.anomaly("A3")["factor"] if self.cal.in_anomaly("A3", d) else 1.0)
        a1 = self.cal.in_anomaly("A1", d)
        bot_on = self.cal.in_anomaly("A5", d)
        bot_zone = list(self.zones["zone_id"]).index(self.cal.anomaly("A5")["zone_id"])
        cvr_boost = self.cal.anomaly("A4")["cvr_boost"] if self.cal.in_anomaly("A4", d) else 1.0

        # candidate pools for the day
        pools = {}
        for z in range(self.nz):
            base = active & self.c_zone[:, z]
            pools[(0, z, -1)] = np.flatnonzero(base & (self.c_surface == 0))
            pools[(2, z, -1)] = np.flatnonzero(base & (self.c_surface == 2))
            im = base & (self.c_surface == 1)
            for k in range(len(self.cats)):
                pools[(1, z, k)] = np.flatnonzero(im & ((self.c_cat == k) | (self.c_cat == -2)))
        cum = {"food": self._cum_share("food"), "instamart": self._cum_share("instamart"), "home": self._cum_share("home")}

        req_rows, imp_rows, clk_rows = [], [], []
        for h in range(24):
            hour_f = hour_ctr_factor(cfg, h)
            thr = {v: pacing_throttle(spent, budget, cum[v][h]) * 0.92 for v in cum}
            hour_charge = []   # (camp, z, surface, pos, units, amount)
            live_spent = spent.copy()   # running spend inside the hour (stops bidding at budget)
            for si, surf in enumerate(SURFACES):
                sc = S[surf]
                npos = sc["positions"]
                vert = ["food", "instamart", "home"][si]
                reserve = banner_reserve if si == 2 else sc["reserve"]
                for z in range(self.nz):
                    r_plat = sess[vert][z, h, :]
                    if r_plat.sum() == 0:
                        continue
                    if si == 1:   # Instamart: split searches across categories
                        cells = [(k, rng.multinomial(r_plat[p], self.cat_w)) for p in range(2) for k in [None]]
                        by_cat = np.stack([cells[0][1], cells[1][1]], axis=1)   # [cat, platform]
                        cell_list = [(k, by_cat[k]) for k in range(len(self.cats)) if by_cat[k].sum() > 0]
                    else:
                        cell_list = [(-1, r_plat)]
                    for k, rp in cell_list:
                        pool = pools[(si, z, k)]
                        tot = int(rp.sum())
                        nb = int(np.clip(np.ceil(tot / (40 if si == 1 else 120)), 1, 8))
                        batches = [rp] if nb == 1 else [np.array(x) for x in zip(*[rng.multinomial(rp[p], np.ones(nb) / nb) for p in range(2)])]
                        for rb in batches:
                            nreq = int(rb.sum())
                            if nreq == 0:
                                continue
                            if pool.size:
                                enter = pool[(rng.random(pool.size) < thr[vert][pool] * self.p_elig[pool])
                                             & self.c_open[pool, h] & (live_spent[pool] < budget[pool])]
                            else:
                                enter = pool
                            if si == 2:
                                res = gsp(bids[enter], np.ones(enter.size), reserve, npos, rng, 0.0)
                            else:
                                res = gsp(bids[enter], sc["base_ctr"] * self.quality[enter], reserve, npos, rng)
                            nfill = res.winners.size
                            for pos in range(npos):
                                filled = pos < nfill
                                for p in range(2):
                                    if rb[p] == 0:
                                        continue
                                    req_rows.append((h, z, si, pos + 1, p, int(rb[p]), int(rb[p]) if filled else 0,
                                                     res.n_bidders * int(rb[p]),
                                                     int(rb[p]) if filled and res.reserve_bound[pos] else 0,
                                                     float(res.prices[pos]) * int(rb[p]) if filled else 0.0, k))
                            for pos in range(nfill):
                                ci = enter[res.winners[pos]]
                                price = float(res.prices[pos])
                                for p in range(2):
                                    n_imp = int(rb[p])
                                    if n_imp == 0:
                                        continue
                                    extra = 0.58 if (a1 and si == 0 and pos == 0 and p == 0) else 1.0
                                    ctr = true_ctr(sc["base_ctr"], sc["pos_decay"][pos], hour_f,
                                                   self.quality[ci], fat[ci], extra)
                                    n_clk = int(rng.binomial(n_imp, ctr))
                                    n_bot = min(int(rng.binomial(n_clk, self.cal.anomaly("A5")["click_uplift"])), n_imp - n_clk) if (bot_on and z == bot_zone and si < 2) else 0
                                    imp_rows.append((h, z, si, pos + 1, p, ci, n_imp))
                                    imps_today[ci] += n_imp
                                    if n_clk:
                                        clk_rows.append((h, z, si, pos + 1, p, ci, n_clk, price, False))
                                    if n_bot:
                                        clk_rows.append((h, z, si, pos + 1, p, ci, n_bot, price, True))
                                    if si == 2:
                                        hour_charge.append((ci, z, si, pos + 1, n_imp, n_imp * price / 1000.0))
                                        live_spent[ci] += n_imp * price / 1000.0
                                    elif n_clk + n_bot:
                                        hour_charge.append((ci, z, si, pos + 1, n_clk + n_bot, (n_clk + n_bot) * price))
                                        live_spent[ci] += (n_clk + n_bot) * price
            # budget cap: anything above the daily budget is delivered free (not billed)
            if hour_charge:
                hc = np.array(hour_charge, dtype=float)
                cidx = hc[:, 0].astype(int)
                amt_by_c = np.bincount(cidx, weights=hc[:, 5], minlength=len(budget))
                allowed = np.maximum(budget - spent, 0.0)
                scale = np.where(amt_by_c > allowed, allowed / np.maximum(amt_by_c, 1e-9), 1.0)
                hc[:, 5] = np.round(hc[:, 5] * scale[cidx], 4)
                spent += np.bincount(cidx, weights=hc[:, 5], minlength=len(budget))
                bill = pd.DataFrame(hc, columns=["c", "z", "s", "position", "billed_units", "amount"])
                bill["hour"] = h
                self._bill_buf.append(bill)
        self.prev_imps = imps_today
        return sess, active, budget, bids, spent, req_rows, imp_rows, clk_rows

    # ------------------------------------------------------------------ main loop
    def run(self, verbose: bool = True):
        cfg, rng = self.cfg, self.rng
        zone_ids = self.zones["zone_id"].to_numpy()
        camp_ids = self.camps["campaign_id"].to_numpy()
        adv_ids = self.adv["advertiser_id"].to_numpy()
        n_days = len(self.cal.dates)
        window_end = self.cal.dates[-1] + pd.Timedelta(days=1)
        user_offset = np.arange(self.nz) * 1_000_000 + 1_000_000
        bot_users = user_offset[list(zone_ids).index(self.cal.anomaly("A5")["zone_id"])] + rng.choice(USERS_PER_ZONE, BOT_USERS, replace=False)
        b = cfg["behaviour"]
        t0 = time.time()
        for di, d in enumerate(self.cal.dates):
            self._bill_buf = []
            wk = self.cal.week_of(d)
            cvr_boost = self.cal.anomaly("A4")["cvr_boost"] if self.cal.in_anomaly("A4", d) else 1.0
            sess, active, budget, bids, spent, req_rows, imp_rows, clk_rows = self.simulate_day(di, d)
            ds = d.date()

            # --- ad requests (hourly aggregate from the ad server)
            rq = pd.DataFrame(req_rows, columns=["hour", "z", "s", "position", "p", "ad_requests", "filled_requests",
                                                 "bidders_sum", "reserve_bound_count", "clearing_price_sum", "k"])
            rq = rq.groupby(["hour", "z", "s", "position", "p", "k"], as_index=False)[
                ["ad_requests", "filled_requests", "bidders_sum", "reserve_bound_count", "clearing_price_sum"]].sum()
            rq.insert(0, "event_date", ds)
            self.out["ad_requests"].append(rq)

            # --- impressions (hourly aggregate per campaign)
            im = pd.DataFrame(imp_rows, columns=["hour", "z", "s", "position", "p", "c", "impressions"])
            im = im.groupby(["hour", "z", "s", "position", "p", "c"], as_index=False)["impressions"].sum()
            im.insert(0, "event_date", ds)
            self.out["impressions"].append(im)

            # --- click events
            if clk_rows:
                ck = pd.DataFrame(clk_rows, columns=["hour", "z", "s", "position", "p", "c", "n", "price", "bot"])
                rep = ck.loc[ck.index.repeat(ck["n"])].reset_index(drop=True)
                n = len(rep)
                secs = rep["hour"].to_numpy() * 3600 + rng.integers(0, 3600, n)
                ts = d + pd.to_timedelta(secs, unit="s")
                users = user_offset[rep["z"].to_numpy()] + rng.integers(0, USERS_PER_ZONE, n)
                isbot = rep["bot"].to_numpy()
                users[isbot] = rng.choice(bot_users, isbot.sum())
                ev = pd.DataFrame({"click_ts": ts, "user_id": users, "c": rep["c"].to_numpy(), "z": rep["z"].to_numpy(),
                                   "s": rep["s"].to_numpy(), "position": rep["position"].to_numpy(), "p": rep["p"].to_numpy(),
                                   "bot": isbot})
                # orders from genuine clicks
                g = ev[~ev["bot"]]
                ci = g["c"].to_numpy()
                conv = np.zeros(len(g))
                for si, surf in enumerate(SURFACES):
                    m = g["s"].to_numpy() == si
                    conv[m] = cvr(cfg, surf, self.rating[ci[m]], self.price_ref[ci[m]]) * cvr_boost
                buy = rng.random(len(g)) < conv
                go = g[buy]
                if len(go):
                    delays = order_delays_seconds(rng, len(go), b["order_delay_median_min"], b["order_delay_late_share"])
                    vals = np.zeros(len(go))
                    for si, surf in enumerate(SURFACES):
                        m = go["s"].to_numpy() == si
                        vals[m] = order_values(rng, surf, self.price_ref[go["c"].to_numpy()[m]])
                    od = pd.DataFrame({
                        "order_ts": go["click_ts"].to_numpy() + pd.to_timedelta(delays, unit="s").to_numpy(),
                        "user_id": go["user_id"].to_numpy(), "a": self.c_adv[go["c"].to_numpy()],
                        "z": go["z"].to_numpy(), "vertical": np.where(go["s"].to_numpy() == 0, "food", "instamart"),
                        "order_value": vals, "_late": delays > 24 * 3600, "_click_week": wk,
                        "_incremental": rng.random(len(go)) < b["incremental_share"],
                    })
                    od = od[od["order_ts"] < window_end]
                    self.out["orders"].append(od)
                # double taps (deduplicated downstream: same user+campaign within 30s)
                dup = ev[(~ev["bot"]) & (rng.random(len(ev)) < b["duplicate_click_rate"])].copy()
                dup["click_ts"] = dup["click_ts"] + pd.to_timedelta(rng.integers(2, 26, len(dup)), unit="s")
                logged = pd.concat([ev, dup], ignore_index=True)
                if self.cal.in_anomaly("A6", d):   # tracking bug: events lost from the log, billing unaffected
                    logged = logged[rng.random(len(logged)) >= self.cal.anomaly("A6")["drop_share"]]
                logged = logged.sort_values("click_ts", kind="stable").drop(columns="bot")
                self.out["clicks"].append(logged)

            # --- billing
            if self._bill_buf:
                bl = pd.concat(self._bill_buf)
                bl = bl.groupby(["c", "z", "s", "position"], as_index=False)[["billed_units", "amount"]].sum()
                bl.insert(0, "billing_date", ds)
                self.out["billing"].append(bl)
                spend_by_adv = np.bincount(self.c_adv[bl["c"].astype(int)], weights=bl["amount"], minlength=len(adv_ids))
                self.week_spend[wk] = self.week_spend.get(wk, 0) + spend_by_adv

            # --- daily budget snapshot for live campaigns
            live = np.flatnonzero((self.c_start <= di) & (di <= self.c_end))
            status = np.where(self.churned[self.c_adv[live]], "churned",
                              np.where(active[live], "active", "paused"))
            self.out["budget_daily"].append(pd.DataFrame({"budget_date": ds, "c": live, "daily_budget": np.round(budget[live], 2),
                                                          "bid": np.round(self.camps["bid"].to_numpy()[live], 2), "status": status}))

            # --- platform totals (all orders, ad and organic) for take rate
            rows = []
            for vert in ("food", "instamart"):
                s_z = sess[vert].sum(axis=(1, 2))
                conv = PLATFORM_CONV[vert] * (cvr_boost if vert in ("food", "instamart") else 1)
                orders = rng.binomial(s_z, conv)
                gov = np.round(orders * PLATFORM_AOV[vert] * rng.lognormal(0, 0.03, self.nz), 0)
                rows.append(pd.DataFrame({"order_date": ds, "zone_id": zone_ids, "vertical": vert, "sessions": s_z,
                                          "orders": orders, "gov": gov}))
            self.out["platform_daily"].append(pd.concat(rows))

            # --- weekly lifecycle at the end of each Sunday
            if d.dayofweek == 6:
                self._lifecycle(wk)
            if verbose and (di % 14 == 13 or di == n_days - 1):
                print(f"  simulated {ds}  (week {wk:2d})  {time.time() - t0:6.1f}s", flush=True)

    def _lifecycle(self, wk: int):
        adv_ids = self.adv["advertiser_id"]
        spend = pd.Series(self.week_spend.get(wk, np.zeros(len(adv_ids))), index=adv_ids)
        gmv = np.zeros(len(adv_ids))
        for od in self.out["orders"][-7:]:
            m = (~od["_late"]) & (od["_click_week"] == wk)
            gmv += np.bincount(od.loc[m, "a"], weights=od.loc[m, "order_value"], minlength=len(adv_ids))
        self.lifecycle_log += weekly_update(self.cfg, wk, self.adv, self.camps, spend,
                                            pd.Series(gmv, index=adv_ids), self.churned, self.rng)

    # ------------------------------------------------------------------ output
    def write(self, out_dir: str | Path, key_dir: str | Path):
        out_dir, key_dir = Path(out_dir), Path(key_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        key_dir.mkdir(parents=True, exist_ok=True)
        zone_ids = self.zones["zone_id"].to_numpy()
        camp_ids = self.camps["campaign_id"].to_numpy()
        adv_ids = self.adv["advertiser_id"].to_numpy()
        surf = np.array(SURFACES)
        plat = np.array(PLATFORMS)

        def save(df, name, chunk=500_000):
            """Stream to one gzip file in chunks (keeps peak memory low on big tables)."""
            with gzip.GzipFile(out_dir / f"{name}.csv.gz", "wb", mtime=0) as gz, io.TextIOWrapper(gz, encoding="utf-8", newline="") as fh:
                for i in range(0, max(len(df), 1), chunk):
                    df.iloc[i:i + chunk].to_csv(fh, index=False, header=(i == 0), date_format="%Y-%m-%d %H:%M:%S")
            print(f"  wrote {name:<28} {len(df):>12,} rows")

        save(self.zones[["zone_id", "name", "lat", "lon"]].rename(columns={"name": "zone_name"}), "raw_zones")
        save(self.adv[["advertiser_id", "name", "advertiser_type", "segment", "is_chain", "category", "home_zone",
                       "rating", "cost_for_two", "joined_on", "name_source"]].rename(columns={"name": "advertiser_name"}),
             "raw_advertisers")
        ci = self.camps_initial
        save(ci[["campaign_id", "advertiser_id", "product", "billing_type", "target_zones", "start_date", "end_date",
                 "daily_budget", "bid", "category"]].rename(columns={"daily_budget": "initial_daily_budget"}), "raw_campaigns")

        bd = pd.concat(self.out.pop("budget_daily"))
        bd.insert(1, "campaign_id", camp_ids[bd.pop("c")])
        save(bd, "raw_campaign_budget_daily"); del bd; gc.collect()

        rq = pd.concat(self.out.pop("ad_requests"))
        cat_names = np.array(self.cats + ["food", "home"])
        rq = rq.assign(zone_id=zone_ids[rq["z"]], surface=surf[rq["s"]], platform=plat[rq["p"]],
                       category=np.where(rq["s"] == 0, "food", np.where(rq["s"] == 2, "home", cat_names[rq["k"].clip(0)])))
        rq["clearing_price_sum"] = rq["clearing_price_sum"].round(2)
        save(rq[["event_date", "hour", "zone_id", "surface", "category", "position", "platform", "ad_requests", "filled_requests",
                 "bidders_sum", "reserve_bound_count", "clearing_price_sum"]], "raw_ad_requests")
        del rq; gc.collect()

        im = pd.concat(self.out.pop("impressions"))
        im = im.assign(zone_id=zone_ids[im["z"]], surface=surf[im["s"]], platform=plat[im["p"]], campaign_id=camp_ids[im["c"]])
        save(im[["event_date", "hour", "zone_id", "surface", "position", "platform", "campaign_id", "impressions"]], "raw_impressions")
        del im; gc.collect()

        ck = pd.concat(self.out.pop("clicks"), ignore_index=True)
        ck.insert(0, "click_id", "CLK" + pd.Series(np.arange(1, len(ck) + 1)).astype(str).str.zfill(9))
        ck = ck.assign(campaign_id=pd.Categorical(camp_ids[ck["c"]]), zone_id=pd.Categorical(zone_ids[ck["z"]]),
                       surface=pd.Categorical(surf[ck["s"]]), platform=pd.Categorical(plat[ck["p"]]))
        save(ck[["click_id", "click_ts", "user_id", "campaign_id", "zone_id", "surface", "position", "platform"]], "raw_clicks")
        del ck; gc.collect()

        od = pd.concat(self.out.pop("orders"), ignore_index=True).sort_values("order_ts", kind="stable").reset_index(drop=True)
        od.insert(0, "order_id", "ORD" + pd.Series(np.arange(1, len(od) + 1)).astype(str).str.zfill(9))
        od = od.assign(advertiser_id=adv_ids[od["a"]], zone_id=zone_ids[od["z"]])
        truth = od[["order_id", "_late", "_incremental"]].rename(columns=lambda c: c.lstrip("_"))
        save(od[["order_id", "order_ts", "user_id", "advertiser_id", "zone_id", "vertical", "order_value"]], "raw_orders")

        bl = pd.concat(self.out.pop("billing"), ignore_index=True)
        bl = bl.assign(campaign_id=camp_ids[bl["c"].astype(int)], zone_id=zone_ids[bl["z"].astype(int)],
                       surface=surf[bl["s"].astype(int)], position=bl["position"].astype(int),
                       billed_units=bl["billed_units"].astype(int), gross_amount=bl["amount"].round(2))
        bl["billing_type"] = np.where(bl["surface"] == "home_banner", "CPM", "CPC")
        bl = bl[bl["billed_units"] > 0]   # keep zero-charge lines: clicks delivered free after a budget cap
        bl.insert(0, "billing_line_id", "BIL" + pd.Series(np.arange(1, len(bl) + 1), index=bl.index).astype(str).str.zfill(9))
        save(bl[["billing_line_id", "billing_date", "zone_id", "surface", "position", "campaign_id", "billing_type",
                 "billed_units", "gross_amount"]], "raw_billing")

        # make-goods / disputes credited back (small, random) -> net revenue
        rng = np.random.default_rng(self.cfg["seed"] + 1)
        adj = bl.sample(frac=0.012, random_state=int(rng.integers(1e9)))
        adj = pd.DataFrame({"adjustment_id": [f"ADJ{i:07d}" for i in range(1, len(adj) + 1)],
                            "billing_line_id": adj["billing_line_id"].to_numpy(),
                            "adjustment_date": (pd.to_datetime(adj["billing_date"]) + pd.to_timedelta(rng.integers(2, 10, len(adj)), unit="D")).dt.date,
                            "reason": rng.choice(["advertiser_dispute", "make_good", "invalid_traffic_credit"], len(adj), p=[0.5, 0.3, 0.2]),
                            "credit_amount": np.round(adj["gross_amount"].to_numpy() * rng.uniform(0.2, 1.0, len(adj)), 2)})
        save(adj, "raw_billing_adjustments")

        save(pd.concat(self.out["platform_daily"]), "raw_platform_daily")

        # ---- answer key + hidden truth (never read by dbt / dashboard)
        anom.answer_key(self.cfg, self.paused_brand).to_csv(key_dir / "anomalies.csv", index=False)
        truth.to_csv(key_dir / "order_truth.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
        pd.DataFrame(self.lifecycle_log).to_csv(key_dir / "lifecycle_log.csv", index=False)
        self.adv[["advertiser_id", "patience", "true_quality", "monthly_budget", "join_week"]].to_csv(key_dir / "advertiser_truth.csv", index=False)
        print(f"  answer key -> {key_dir}/anomalies.csv")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="config/sim_config.yaml")
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--answer-key", default="data/answer_key")
    ap.add_argument("--external", default="data/external")
    ap.add_argument("--weeks", type=int, default=None, help="override number of weeks (for quick tests)")
    args = ap.parse_args()
    cfg = load_config(args.config)
    t = time.time()
    sim = Simulator(cfg, Path(args.external), weeks=args.weeks)
    print(f"Simulating {cfg['calendar']['weeks']} weeks | {len(sim.adv):,} advertisers | {len(sim.camps):,} campaigns "
          f"| seed {cfg['seed']} (ALL DATA SIMULATED)")
    sim.run()
    sim.write(args.out, args.answer_key)
    print(f"Done in {time.time() - t:.0f}s")


if __name__ == "__main__":
    main()
