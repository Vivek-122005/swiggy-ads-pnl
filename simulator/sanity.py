"""Quick plausibility report on raw simulator output (pandas only, no warehouse needed).

    python -m simulator.sanity --raw data/raw [--charts analysis/sanity]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def load(raw: Path, name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(raw / f"{name}.csv.gz", **kw)


def report(raw: Path, charts: Path | None = None) -> dict:
    rq = load(raw, "raw_ad_requests")
    im = load(raw, "raw_impressions")
    ck = load(raw, "raw_clicks", parse_dates=["click_ts"])
    od = load(raw, "raw_orders", parse_dates=["order_ts"])
    bl = load(raw, "raw_billing")
    bd = load(raw, "raw_campaign_budget_daily")
    pf = load(raw, "raw_platform_daily")
    cp = load(raw, "raw_campaigns")

    # dedupe double taps: same user + campaign within 30s
    ck = ck.sort_values(["user_id", "campaign_id", "click_ts"])
    gap = ck.groupby(["user_id", "campaign_id"])["click_ts"].diff().dt.total_seconds()
    ck = ck[~(gap <= 30)]

    out = {}
    out["days"] = rq["event_date"].nunique()
    out["ad_requests"] = int(rq["ad_requests"].sum())
    out["impressions"] = int(im["impressions"].sum())
    out["fill_rate"] = rq["filled_requests"].sum() / rq["ad_requests"].sum()
    out["valid_clicks"] = len(ck)
    out["ctr"] = len(ck) / im["impressions"].sum()
    out["gross_revenue"] = bl["gross_amount"].sum()
    out["cpc"] = bl.loc[bl.billing_type == "CPC", "gross_amount"].sum() / bl.loc[bl.billing_type == "CPC", "billed_units"].sum()
    out["ecpm"] = bl["gross_amount"].sum() / im["impressions"].sum() * 1000
    out["bid_density"] = rq["bidders_sum"].sum() / rq["ad_requests"].sum()
    out["reserve_binding_rate"] = rq["reserve_bound_count"].sum() / rq["filled_requests"].sum()
    out["take_rate"] = bl["gross_amount"].sum() / pf["gov"].sum()

    # attribution: last click, same user + advertiser, within 24h
    ck2 = ck.merge(cp[["campaign_id", "advertiser_id"]], on="campaign_id")
    m = od.merge(ck2[["user_id", "advertiser_id", "click_ts", "click_id"]], on=["user_id", "advertiser_id"])
    m = m[(m.click_ts <= m.order_ts) & (m.order_ts - m.click_ts <= pd.Timedelta(hours=24))]
    m = m.sort_values("click_ts").groupby("order_id").tail(1)
    out["attributed_orders"] = len(m)
    out["attributed_gmv"] = m["order_value"].sum()
    out["roas"] = m["order_value"].sum() / bl["gross_amount"].sum()
    out["cvr"] = len(m) / len(ck)

    spend_c = bl.groupby("campaign_id")["gross_amount"].sum()
    bud_c = bd[bd.status == "active"].groupby("campaign_id")["daily_budget"].sum()
    util = (spend_c.reindex(bud_c.index).fillna(0) / bud_c)
    out["budget_util_overall"] = spend_c.sum() / bud_c.sum()
    out["budget_util_median_campaign"] = util.median()
    out["active_advertisers"] = cp.set_index("campaign_id").loc[spend_c.index, "advertiser_id"].nunique()

    imp_c = im.groupby(["surface", "position"])["impressions"].sum()
    clk_c = ck.groupby(["surface", "position"]).size()
    out["ctr_by_position"] = (clk_c / imp_c).round(4).to_dict()
    fill_h = rq.groupby("hour")[["filled_requests", "ad_requests"]].sum()
    out["fill_by_hour"] = (fill_h.filled_requests / fill_h.ad_requests).round(3).to_dict()
    fill_s = rq.groupby("surface")[["filled_requests", "ad_requests"]].sum()
    out["fill_by_surface"] = (fill_s.filled_requests / fill_s.ad_requests).round(3).to_dict()
    rev_s = bl.groupby("surface")["gross_amount"].sum()
    out["revenue_share_by_surface"] = (rev_s / rev_s.sum()).round(3).to_dict()
    top10 = bl.merge(cp[["campaign_id", "advertiser_id"]]).groupby("advertiser_id")["gross_amount"].sum().nlargest(10).sum()
    out["top10_concentration"] = top10 / bl["gross_amount"].sum()

    if charts:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        charts.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(1, 3, figsize=(15, 4))
        (clk_c / imp_c).unstack(0).plot(marker="o", ax=ax[0], title="CTR by position (should decay)")
        rq.groupby("hour")["ad_requests"].sum().plot(ax=ax[1], title="Ad requests by hour (lunch + dinner peaks)")
        (fill_h.filled_requests / fill_h.ad_requests).plot(ax=ax[2], title="Fill rate by hour")
        fig.tight_layout()
        fig.savefig(charts / "sanity_shapes.png", dpi=110)
        daily = bl.groupby("billing_date")["gross_amount"].sum()
        fig, ax = plt.subplots(figsize=(14, 4))
        daily.plot(ax=ax, title="Daily gross ad revenue (INR, simulated)")
        fig.tight_layout()
        fig.savefig(charts / "sanity_daily_revenue.png", dpi=110)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--charts", default=None)
    a = ap.parse_args()
    r = report(Path(a.raw), Path(a.charts) if a.charts else None)
    for k, v in r.items():
        if isinstance(v, float):
            v = f"{v:,.4f}" if abs(v) < 100 else f"{v:,.0f}"
        print(f"{k:<30} {v}")


if __name__ == "__main__":
    main()
