"""DEV FIXTURE ONLY - builds the dashboard JSON contract straight from raw simulator CSVs with pandas.

    python -m dashboard.mock_data --raw data/raw --out dashboard/site/data

Production data comes from `dashboard/export.py`, which reads the dbt marts (the single source of
truth for every number). This script approximates the same mart logic so the UI can be developed and
screenshot-tested without a warehouse: valid clicks dedupe repeats within 30s, last-click 24h
attribution booked on the click date, weeks Monday-Sunday from 2026-04-27, ratios = sum / sum.
Never publish its output as the dashboard's data.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import math
import re
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
START = pd.Timestamp("2026-04-27")
SURFACES = ["food_listing", "instamart_search", "home_banner"]


def metric_catalogue() -> list[dict]:
    """Parse the dbt macro so the fixture uses the exact same metric definitions."""
    txt = (ROOT / "dbt/macros/metric_catalogue.sql").read_text()
    body = txt[txt.index("return([") + len("return("): txt.rindex("]) }}") + 1]
    body = re.sub(r"\bnone\b", "None", body)
    body = re.sub(r"\btrue\b", "True", body)
    body = re.sub(r"\bfalse\b", "False", body)
    return ast.literal_eval(body)


def wk(s) -> pd.Series:
    return ((pd.to_datetime(s) - START).dt.days // 7 + 1).astype(int)


def load(raw: Path):
    r = lambda n, **k: pd.read_csv(raw / f"{n}.csv.gz", **k)
    t = {n: r(n) for n in ["raw_zones", "raw_advertisers", "raw_campaigns", "raw_campaign_budget_daily",
                           "raw_ad_requests", "raw_impressions", "raw_billing", "raw_billing_adjustments",
                           "raw_platform_daily"]}
    t["raw_clicks"] = r("raw_clicks", parse_dates=["click_ts"])
    t["raw_orders"] = r("raw_orders", parse_dates=["order_ts"])
    return t


def build(raw: Path, out: Path):
    t = load(raw)
    cp = t["raw_campaigns"][["campaign_id", "advertiser_id"]]
    adv = t["raw_advertisers"].rename(columns={"segment": "advertiser_segment"})
    seg = adv.set_index("advertiser_id")["advertiser_segment"]

    # ---- valid clicks + attribution
    ck = t["raw_clicks"].sort_values(["user_id", "campaign_id", "click_ts", "click_id"])
    gap = ck.groupby(["user_id", "campaign_id"])["click_ts"].diff().dt.total_seconds()
    ck = ck[~(gap <= 30)].merge(cp, on="campaign_id")
    ck["week_number"] = wk(ck["click_ts"].dt.normalize())
    od = t["raw_orders"]
    m = od.merge(ck[["user_id", "advertiser_id", "click_ts", "click_id", "zone_id", "surface", "position", "platform",
                     "week_number"]].rename(columns={"zone_id": "click_zone"}), on=["user_id", "advertiser_id"])
    m = m[(m.click_ts <= m.order_ts) & (m.order_ts <= m.click_ts + pd.Timedelta(hours=24))]
    att = m.sort_values(["click_ts", "click_id"]).groupby("order_id").tail(1)
    att = att.drop(columns=["zone_id"]).rename(columns={"click_zone": "zone_id"})   # credit goes to the click's slot

    # ---- weekly advertiser x surface x zone facts
    im = t["raw_impressions"].merge(cp, on="campaign_id")
    im["week_number"] = wk(im["event_date"])
    bl = t["raw_billing"].merge(cp, on="campaign_id")
    cred = t["raw_billing_adjustments"].groupby("billing_line_id")["credit_amount"].sum()
    bl["credit"] = bl["billing_line_id"].map(cred).fillna(0)
    bl["week_number"] = wk(bl["billing_date"])
    k = ["week_number", "surface", "zone_id", "advertiser_id"]
    f = pd.concat([
        im.groupby(k)["impressions"].sum(),
        ck.groupby(k).size().rename("clicks"),
        ck[ck.surface != "home_banner"].groupby(k).size().rename("cpc_clicks"),
        bl[bl.billing_type == "CPC"].groupby(k)["billed_units"].sum().rename("billed_clicks"),
        bl.groupby(k)["gross_amount"].sum().rename("gross_revenue"),
        (bl["gross_amount"] - bl["credit"]).groupby([bl[c] for c in k]).sum().rename("net_revenue"),
        bl[bl.billing_type == "CPC"].groupby(k)["gross_amount"].sum().rename("cpc_revenue"),
        att.groupby(k).size().rename("attributed_orders"),
        att.groupby(k)["order_value"].sum().rename("attributed_gmv"),
    ], axis=1).fillna(0).reset_index()
    f["advertiser_segment"] = f["advertiser_id"].map(seg)

    rq = t["raw_ad_requests"].copy()
    rq["week_number"] = wk(rq["event_date"])
    pdl = t["raw_platform_daily"].copy()
    pdl["week_number"] = wk(pdl["order_date"])
    vert = {"food_listing": "food", "instamart_search": "instamart", "home_banner": "instamart"}

    # ---- cube
    dims = ["surface", "zone_id", "advertiser_segment"]
    add = ["impressions", "clicks", "cpc_clicks", "billed_clicks", "gross_revenue", "net_revenue", "cpc_revenue",
           "attributed_orders", "attributed_gmv"]
    rows = []
    for r_ in range(4):
        for c in combinations(dims, r_):
            g = f.groupby(["week_number", *c, "advertiser_id"])[add].sum().reset_index()
            for d in dims:
                if d not in c:
                    g[d] = "all"
            g["rank"] = g.groupby(["week_number", *dims])["gross_revenue"].rank(ascending=False, method="first")
            agg = g.groupby(["week_number", *dims]).agg(
                **{a: (a, "sum") for a in add},
                active_advertisers=("gross_revenue", lambda x: int((x > 0).sum())),
                median_spend=("gross_revenue", lambda x: float(x[x > 0].median()) if (x > 0).any() else None))
            agg["top10_revenue"] = g[g["rank"] <= 10].groupby(["week_number", *dims])["gross_revenue"].sum()
            rows.append(agg.reset_index())
    cube = pd.concat(rows, ignore_index=True)
    inv_rows = []
    for c in [[], ["surface"], ["zone_id"], ["surface", "zone_id"]]:
        g = rq.groupby(["week_number", *c])[["ad_requests", "filled_requests", "bidders_sum", "reserve_bound_count"]].sum().reset_index()
        for d in ["surface", "zone_id"]:
            if d not in c:
                g[d] = "all"
        inv_rows.append(g)
    inv = pd.concat(inv_rows).rename(columns={"reserve_bound_count": "reserve_binding_count"})
    inv["advertiser_segment"] = "all"
    cube = cube.merge(inv, on=["week_number", *dims], how="left")
    gv = []
    for s, v in vert.items():
        x = pdl[pdl.vertical == v]
        a = x.groupby(["week_number", "zone_id"])["gov"].sum().reset_index(); a["surface"] = s; gv.append(a)
        a = x.groupby("week_number")["gov"].sum().reset_index(); a["surface"] = s; a["zone_id"] = "all"; gv.append(a)
    a = pdl.groupby(["week_number", "zone_id"])["gov"].sum().reset_index(); a["surface"] = "all"; gv.append(a)
    a = pdl.groupby("week_number")["gov"].sum().reset_index(); a["surface"] = "all"; a["zone_id"] = "all"; gv.append(a)
    gv = pd.concat(gv); gv["advertiser_segment"] = "all"
    cube = cube.merge(gv, on=["week_number", *dims], how="left")
    cube["click_gap"] = cube["billed_clicks"] - cube["cpc_clicks"]
    cube["gross_revenue_with_gov"] = np.where(cube["gov"].notna(), cube["gross_revenue"], np.nan)

    # ---- advertiser weekly
    bd = t["raw_campaign_budget_daily"].merge(cp, on="campaign_id")
    bd["week_number"] = wk(bd["budget_date"])
    budget = bd[bd.status == "active"].groupby(["week_number", "advertiser_id"])["daily_budget"].sum()
    spend = bl.groupby(["week_number", "advertiser_id"])["gross_amount"].sum()
    gmv = att.groupby(["week_number", "advertiser_id"])["order_value"].sum()
    first = spend[spend > 0].reset_index().groupby("advertiser_id")["week_number"].min()
    weeks = np.arange(1, 27)
    aw = pd.DataFrame([(w, a) for a, fw in first.items() for w in weeks if w >= fw], columns=["week_number", "advertiser_id"])
    aw["first_active_week"] = aw["advertiser_id"].map(first)
    ix = pd.MultiIndex.from_frame(aw[["week_number", "advertiser_id"]])
    aw["gross_spend"] = spend.reindex(ix).fillna(0).to_numpy()
    aw["budget"] = budget.reindex(ix).fillna(0).to_numpy()
    aw["attributed_gmv"] = gmv.reindex(ix).fillna(0).to_numpy()
    aw = aw.sort_values(["advertiser_id", "week_number"])
    aw["is_active"] = aw["gross_spend"] > 0
    aw["is_new"] = aw["week_number"] == aw["first_active_week"]
    act = aw["is_active"].astype(int)
    prev = aw.groupby("advertiser_id")["is_active"].shift(1).fillna(False).astype(bool)
    fut = act[::-1].groupby(aw["advertiser_id"][::-1]).rolling(4, min_periods=1).sum().reset_index(level=0, drop=True)[::-1]
    nfut = act[::-1].groupby(aw["advertiser_id"][::-1]).rolling(4, min_periods=1).count().reset_index(level=0, drop=True)[::-1]
    churn = pd.Series(False, index=aw.index, dtype=object)
    churn[prev & (fut == 0)] = True
    churn[prev & ~aw["is_active"] & (nfut < 4)] = None
    aw["is_churned"] = churn
    aw["roas"] = aw["attributed_gmv"] / aw["gross_spend"].replace(0, np.nan)
    aw["budget_utilisation"] = aw["gross_spend"] / aw["budget"].replace(0, np.nan)

    acc = aw.groupby("week_number").agg(
        account_gross_spend=("gross_spend", "sum"),
        account_budget=("budget", lambda x: x[aw.loc[x.index, "is_active"]].sum()),
        new_advertisers=("is_new", "sum"),
        churned_raw=("is_churned", lambda x: int((x == True).sum())),  # noqa: E712
        pending=("is_churned", lambda x: int(x.isna().sum())))
    acc["churned_advertisers"] = np.where(acc["pending"] == 0, acc["churned_raw"], np.nan)

    # ---- kpi_weekly
    cat = metric_catalogue()
    base = cube[(cube.zone_id == "all") & (cube.advertiser_segment == "all")].copy().rename(columns={"surface": "product"})
    base = base.merge(acc[["account_gross_spend", "account_budget", "new_advertisers", "churned_advertisers"]],
                      left_on="week_number", right_index=True, how="left")
    for c in ["account_gross_spend", "account_budget", "new_advertisers", "churned_advertisers"]:
        base.loc[base["product"] != "all", c] = np.nan
    base = base.sort_values(["product", "week_number"])
    comps = sorted({c for m_ in cat for c in (m_["num"], m_["den"]) if c})
    g = base.groupby("product")
    for c in comps:
        base[f"prev_{c}"] = g[c].shift(1)
        base[f"p4_{c}"] = g[c].transform(lambda s: s.shift(1).rolling(4, min_periods=1).sum())
        base[f"n4_{c}"] = g[c].transform(lambda s: s.shift(1).notna().astype(int).rolling(4, min_periods=1).sum())
    kp = []
    div = lambda a, b: a / b.replace(0, np.nan)
    for i, m_ in enumerate(cat, 1):
        n, d, sc = m_["num"], m_["den"], m_["scale"]
        x = base[["week_number", "product"]].copy()
        x["metric"], x["metric_order"] = m_["metric"], i
        if d:
            x["value"] = div(base[n], base[d]) * sc
            x["prior_week_value"] = div(base[f"prev_{n}"], base[f"prev_{d}"]) * sc
            x["four_week_avg"] = div(base[f"p4_{n}"], base[f"p4_{d}"]) * sc
        else:
            x["value"] = base[n] * sc
            x["prior_week_value"] = base[f"prev_{n}"] * sc
            x["four_week_avg"] = div(base[f"p4_{n}"], base[f"n4_{n}"]) * sc
        kp.append(x)
    kp = pd.concat(kp)
    kp = kp[kp["value"].notna()].copy()
    kp["wow_pct"] = (kp["value"] - kp["prior_week_value"]) / kp["prior_week_value"].abs().replace(0, np.nan)
    kp["vs_4wk_pct"] = (kp["value"] - kp["four_week_avg"]) / kp["four_week_avg"].abs().replace(0, np.nan)
    kp["week_start"] = (START + pd.to_timedelta((kp["week_number"] - 1) * 7, unit="D")).dt.strftime("%Y-%m-%d")
    meta_c = pd.DataFrame(cat)
    meta_c["metric_order"] = range(1, len(cat) + 1)

    # ---- bridge
    bb = cube[(cube.zone_id == "all") & (cube.advertiser_segment == "all") & (cube.surface != "all")].copy()
    bb["q"] = bb["ad_requests"]; bb["f"] = bb["filled_requests"] / bb["ad_requests"]
    ban = bb["surface"] == "home_banner"
    bb["c"] = np.where(ban, 1.0, bb["clicks"] / bb["impressions"])
    bb["p"] = np.where(ban, bb["gross_revenue"] / bb["impressions"], bb["gross_revenue"] / bb["clicks"])
    pr = bb[["week_number", "surface", "q", "f", "c", "p", "gross_revenue"]].copy(); pr["week_number"] += 1
    br = bb.merge(pr, on=["week_number", "surface"], suffixes=("1", "0"))
    br["requests_effect"] = (br.q1 - br.q0) * br.f0 * br.c0 * br.p0
    br["fill_effect"] = br.q1 * (br.f1 - br.f0) * br.c0 * br.p0
    br["ctr_effect"] = br.q1 * br.f1 * (br.c1 - br.c0) * br.p0
    br["price_effect"] = br.q1 * br.f1 * br.c1 * (br.p1 - br.p0)
    br = br.rename(columns={"gross_revenue0": "revenue_prior", "gross_revenue1": "revenue_current", "q0": "requests_prior",
                            "q1": "requests_current", "f0": "fill_prior", "f1": "fill_current"})
    br["revenue_change"] = br.revenue_current - br.revenue_prior
    br["residual"] = br.revenue_change - br[["requests_effect", "fill_effect", "ctr_effect", "price_effect"]].sum(axis=1)
    bn = br["surface"] == "home_banner"
    br["ctr_prior"] = np.where(bn, np.nan, br.c0); br["ctr_current"] = np.where(bn, np.nan, br.c1)
    br["price_prior"] = np.where(bn, br.p0 * 1000, br.p0); br["price_current"] = np.where(bn, br.p1 * 1000, br.p1)
    tot = br.groupby("week_number")[["revenue_prior", "revenue_current", "revenue_change", "requests_effect", "fill_effect",
                                     "ctr_effect", "price_effect", "residual", "requests_prior", "requests_current"]].sum().reset_index()
    tot["surface"] = "all"
    br = pd.concat([br, tot], ignore_index=True)

    # ---- movers
    mv = kp[(kp["product"] == "all") & kp["four_week_avg"].notna()
            & ~kp["metric"].isin(["net_ad_revenue", "attributed_gmv", "impressions", "clicks", "attributed_orders", "median_spend"])].copy()
    mv["score"] = np.where(mv["metric"] == "click_log_gap", mv["value"].abs() * 10, mv["vs_4wk_pct"].abs().fillna(0))
    mv = mv.sort_values(["week_number", "score", "metric"], ascending=[True, False, True])
    mv["mover_rank"] = mv.groupby("week_number").cumcount() + 1
    mv = mv[mv["mover_rank"] <= 3].merge(meta_c[["metric", "label", "unit", "good"]], on="metric")
    mv = mv.rename(columns={"label": "metric_label", "good": "good_direction"})

    # ---- zones / categories
    z = cube[(cube.surface == "all") & (cube.advertiser_segment == "all") & (cube.zone_id != "all")].copy()
    z = z.merge(t["raw_zones"], on="zone_id").sort_values(["zone_id", "week_number"])
    z["ctr"] = z.clicks / z.impressions; z["cvr"] = z.attributed_orders / z.clicks
    z["roas"] = z.attributed_gmv / z.gross_revenue; z["fill_rate"] = z.filled_requests / z.ad_requests
    p4 = z.groupby("zone_id")["gross_revenue"].transform(lambda s: s.shift(1).rolling(4, min_periods=1).mean())
    z["revenue_vs_4wk_pct"] = (z.gross_revenue - p4) / p4
    fa = f.merge(adv[["advertiser_id", "advertiser_type", "category"]], on="advertiser_id")
    cg = fa.groupby(["week_number", "advertiser_type", "category"]).agg(
        gross_revenue=("gross_revenue", "sum"), impressions=("impressions", "sum"), clicks=("clicks", "sum"),
        attributed_orders=("attributed_orders", "sum"), attributed_gmv=("attributed_gmv", "sum")).reset_index()
    act_c = fa[fa.gross_revenue > 0].groupby(["week_number", "advertiser_type", "category"])["advertiser_id"].nunique()
    cg["active_advertisers"] = cg.set_index(["week_number", "advertiser_type", "category"]).index.map(act_c).fillna(0).astype(int)
    cg["ctr"] = cg.clicks / cg.impressions; cg["cvr"] = cg.attributed_orders / cg.clicks; cg["roas"] = cg.attributed_gmv / cg.gross_revenue
    cg = cg.sort_values(["advertiser_type", "category", "week_number"])
    p4 = cg.groupby(["advertiser_type", "category"])["gross_revenue"].transform(lambda s: s.shift(1).rolling(4, min_periods=1).mean())
    cg["spend_vs_4wk_pct"] = (cg.gross_revenue - p4) / p4

    # ---- cohorts
    aw["weeks_since_first"] = aw["week_number"] - aw["first_active_week"]
    co = aw.groupby(["first_active_week", "weeks_since_first"]).agg(active_advertisers=("is_active", "sum")).reset_index()
    size = aw.groupby("first_active_week")["advertiser_id"].nunique()
    co["cohort_size"] = co["first_active_week"].map(size)
    co["retention"] = co["active_advertisers"] / co["cohort_size"]
    co = co.rename(columns={"first_active_week": "cohort_week"})

    # ---- inventory
    hm = rq.groupby(["week_number", "zone_id", "hour"])[["ad_requests", "filled_requests"]].sum().reset_index()
    hm["fill_rate"] = hm.filled_requests / hm.ad_requests
    rq["unfilled"] = rq.ad_requests - rq.filled_requests
    isf = rq.groupby(["week_number", "surface", "category"]).agg(ad_requests=("ad_requests", "sum"), filled_requests=("filled_requests", "sum"),
                                                                unfilled_requests=("unfilled", "sum"), b=("bidders_sum", "sum"),
                                                                r=("reserve_bound_count", "sum"), cp=("clearing_price_sum", "sum")).reset_index()
    isf["fill_rate"] = isf.filled_requests / isf.ad_requests; isf["bid_density"] = isf.b / isf.ad_requests
    isf["reserve_binding_rate"] = isf.r / isf.filled_requests.replace(0, np.nan); isf["avg_clearing_price"] = isf.cp / isf.filled_requests.replace(0, np.nan)
    up = rq[rq.hour.isin([12, 13, 19, 20, 21]) & rq.category.isin(["food", "home"])].groupby(
        ["week_number", "zone_id", "surface", "hour"])[["unfilled", "ad_requests", "filled_requests"]].sum().reset_index()
    up["fill_rate"] = up.filled_requests / up.ad_requests
    up = up.sort_values(["week_number", "unfilled"], ascending=[True, False])
    hr = rq.groupby(["event_date", "hour", "zone_id", "surface", "category", "position"])[["filled_requests", "clearing_price_sum"]].sum().reset_index()
    hr = hr[hr.filled_requests > 0]
    hr["price_bucket"] = np.floor(hr.clearing_price_sum / hr.filled_requests)
    hr["week_number"] = wk(hr["event_date"])
    cpd = hr.groupby(["week_number", "surface", "price_bucket"])["filled_requests"].sum().reset_index()

    # ---- platform
    im2 = t["raw_impressions"].copy(); im2["week_number"] = wk(im2["event_date"])
    kk = ["week_number", "surface", "position", "platform"]
    pw = pd.concat([im2.groupby(kk)["impressions"].sum(), ck.groupby(kk).size().rename("clicks"),
                    att.groupby(kk).size().rename("attributed_orders")], axis=1).fillna(0).reset_index()

    # ---- top advertisers
    ta = aw.merge(adv[["advertiser_id", "advertiser_name", "advertiser_segment", "category"]], on="advertiser_id")
    ta["prior_week_spend"] = ta.groupby("advertiser_id")["gross_spend"].shift(1)
    ta["spend_rank"] = ta.groupby("week_number")["gross_spend"].rank(ascending=False, method="first").astype(int)
    prevtop = ta[ta.spend_rank <= 25][["week_number", "advertiser_id"]].assign(week_number=lambda d: d.week_number + 1)
    keep = ta.merge(prevtop.assign(k=1), on=["week_number", "advertiser_id"], how="left")
    ta = keep[(keep.spend_rank <= 25) | keep.k.notna()].copy()
    ta["spend_wow_pct"] = (ta.gross_spend - ta.prior_week_spend) / ta.prior_week_spend.replace(0, np.nan)
    ta = ta.sort_values(["week_number", "spend_rank"])

    aws = aw.groupby("week_number").agg(active=("is_active", "sum"), new=("is_new", "sum"),
                                        churned=("is_churned", lambda x: int((x == True).sum())),  # noqa: E712
                                        churn_provisional=("is_churned", lambda x: bool(x.isna().any()))).reset_index()
    wkdf = pd.DataFrame({"week_number": weeks})
    wkdf["week_start"] = (START + pd.to_timedelta((wkdf.week_number - 1) * 7, unit="D")).dt.strftime("%Y-%m-%d")
    wkdf["week_end"] = (START + pd.to_timedelta((wkdf.week_number - 1) * 7 + 6, unit="D")).dt.strftime("%Y-%m-%d")

    files = {
        "kpi_weekly": (kp, ["week_number", "week_start", "product", "metric", "metric_order", "value", "prior_week_value", "wow_pct", "four_week_avg", "vs_4wk_pct"]),
        "metrics": (meta_c.rename(columns={"label": "metric_label", "good": "good_direction", "jd": "is_jd_metric"}),
                    ["metric", "metric_order", "metric_label", "unit", "good_direction", "is_jd_metric", "definition"]),
        "kpi_cube": (cube, ["week_number", "surface", "zone_id", "advertiser_segment", "gross_revenue", "net_revenue", "impressions", "clicks", "cpc_clicks",
                            "cpc_revenue", "billed_clicks", "attributed_orders", "attributed_gmv", "active_advertisers", "top10_revenue", "median_spend",
                            "ad_requests", "filled_requests", "bidders_sum", "reserve_binding_count", "gov"]),
        "revenue_bridge": (br, ["week_number", "surface", "revenue_prior", "revenue_current", "revenue_change", "requests_effect", "fill_effect", "ctr_effect",
                                "price_effect", "residual", "requests_prior", "requests_current", "fill_prior", "fill_current", "ctr_prior", "ctr_current",
                                "price_prior", "price_current"]),
        "movers": (mv, ["week_number", "mover_rank", "metric", "metric_label", "unit", "good_direction", "value", "four_week_avg", "vs_4wk_pct", "wow_pct"]),
        "zones": (z.rename(columns={}), ["week_number", "zone_id", "zone_name", "lat", "lon", "gross_revenue", "impressions", "clicks", "attributed_orders",
                                         "attributed_gmv", "active_advertisers", "ctr", "cvr", "roas", "fill_rate", "revenue_vs_4wk_pct"]),
        "categories": (cg, ["week_number", "advertiser_type", "category", "gross_revenue", "impressions", "clicks", "attributed_orders", "attributed_gmv",
                            "active_advertisers", "ctr", "cvr", "roas", "spend_vs_4wk_pct"]),
        "cohorts": (co, ["cohort_week", "weeks_since_first", "cohort_size", "active_advertisers", "retention"]),
        "fill_heatmap": (hm.rename(columns={"hour": "event_hour"}), ["week_number", "zone_id", "event_hour", "ad_requests", "filled_requests", "fill_rate"]),
        "inventory_surface": (isf.rename(columns={"category": "request_category"}),
                              ["week_number", "surface", "request_category", "ad_requests", "filled_requests", "unfilled_requests", "fill_rate", "bid_density",
                               "reserve_binding_rate", "avg_clearing_price"]),
        "unfilled_premium": (up.rename(columns={"hour": "event_hour", "unfilled": "unfilled_requests"}),
                             ["week_number", "zone_id", "surface", "event_hour", "unfilled_requests", "ad_requests", "fill_rate"]),
        "clearing_price_dist": (cpd, ["week_number", "surface", "price_bucket", "filled_requests"]),
        "platform_weekly": (pw.rename(columns={"position": "slot_position"}), ["week_number", "surface", "slot_position", "platform", "impressions", "clicks", "attributed_orders"]),
        "top_advertisers": (ta, ["week_number", "spend_rank", "advertiser_id", "advertiser_name", "advertiser_segment", "category", "gross_spend",
                                 "prior_week_spend", "spend_wow_pct", "budget", "budget_utilisation", "roas", "is_active"]),
        "advertiser_weekly_summary": (aws, ["week_number", "active", "new", "churned", "churn_provisional"]),
        "zones_dim": (t["raw_zones"], ["zone_id", "zone_name", "lat", "lon"]),
        "weeks": (wkdf, ["week_number", "week_start", "week_end"]),
    }
    out.mkdir(parents=True, exist_ok=True)

    def clean(v):
        if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            return None
        if isinstance(v, (np.bool_, bool)):
            return bool(v)
        if isinstance(v, np.integer):
            return int(v)
        if isinstance(v, (np.floating, float)):
            return None if (math.isnan(v) or math.isinf(v)) else round(float(v), 6)
        return v

    for name, (df, cols) in files.items():
        rows_ = [[clean(v) for v in r] for r in df[cols].itertuples(index=False, name=None)]
        (out / f"{name}.json").write_text(json.dumps({"columns": cols, "rows": rows_}, separators=(",", ":")))
        print(f"  {name:<28} {len(rows_):>8,} rows")
    (out / "meta.json").write_text(json.dumps({
        "refreshed_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d %H:%M IST") + " (dev fixture)",
        "data_note": "ALL DATA IS SIMULATED. Restaurant and brand names come from public Kaggle datasets "
                     "(Zomato Bangalore, BigBasket); every ad metric attached to them is invented. Not Swiggy data.",
        "metric_dictionary_url": "https://vivek-122005.github.io/swiggy-ads-pnl/docs/",
        "repo_url": "https://github.com/Vivek-122005/swiggy-ads-pnl",
    }, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="dashboard/site/data")
    a = ap.parse_args()
    build(Path(a.raw), Path(a.out))


if __name__ == "__main__":
    main()
