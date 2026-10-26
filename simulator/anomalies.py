"""Planted events and the answer key.

The answer key (data/answer_key/anomalies.csv) is written OUTSIDE the raw folder and no
dbt model, test or dashboard reads it. WBRs must find these events from the data alone;
the key is only used afterwards to score the analysis.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DESCRIPTIONS = {
    "A1": ("App release moves sponsored slot 1 below the fold on Android",
           "Food listings CTR down ~8%, Android position 1 only", "Rate effect isolated to one platform and position"),
    "A2": ("Top-3 Instamart brand pauses all campaigns",
           "Revenue and top-10 concentration drop; fill rate dips in snacks", "Advertiser page: budget utilisation goes to zero for one account"),
    "A3": ("Reserve price raised 20% on home banners (permanent)",
           "Banner CPM up, banner fill rate down, revenue roughly flat", "Reserve-binding rate jumps; unfilled banner slots rise"),
    "A4": ("Heavy rain for 3 days (Tue-Thu)",
           "Sessions and orders up, CTR flat, ROAS up", "Traffic up across all zones; no change in rates"),
    "A5": ("Invalid-click bot in Whitefield",
           "Clicks up ~30% in Whitefield, CVR collapses there", "CTR up while CVR falls is the classic fraud signature"),
    "A6": ("Tracking bug drops 10% of click events for one day",
           "Logged clicks/CTR down for one day; billing and orders unchanged", "Billed clicks != logged clicks; orders per impression steady = data issue"),
    "A7": ("Navratri-Dussehra festive fortnight (Diwali falls after the window)",
           "Requests, bids and new advertisers spike", "Seasonality, not a problem: compare with festival baseline"),
}


def pick_paused_brand(adv: pd.DataFrame, camps: pd.DataFrame) -> str:
    """Choose the largest snacks brand and make sure it is a top-3 Instamart spender by budget."""
    brands = adv[(adv["advertiser_type"] == "brand")]
    # explicit tie-breakers + stable sorts: identical results on every platform / pandas build
    snacks = brands[brands["category"] == "snacks"].sort_values(["monthly_budget", "advertiser_id"],
                                                                 ascending=[False, True], kind="mergesort")
    target = snacks.iloc[0]["advertiser_id"]
    im = camps[camps["product"] == "instamart_search"]
    by_adv = im.groupby("advertiser_id")["daily_budget"].sum().sort_values(ascending=False, kind="mergesort")
    third = by_adv.iloc[2] if len(by_adv) >= 3 else by_adv.max()
    cur = by_adv.get(target, 0.0)
    m = (camps["advertiser_id"] == target) & (camps["product"] == "instamart_search")
    all_zones = "|".join(sorted({z for tz in camps["target_zones"] for z in tz.split("|")}))
    camps.loc[m, "daily_budget"] *= (max(third, cur) * 1.6) / max(cur, 1.0)   # a top-3 account: ~4-5% of revenue
    camps.loc[m, "bid"] = np.maximum(camps.loc[m, "bid"], im["bid"].quantile(0.9))
    camps.loc[m, "target_zones"] = all_zones
    camps.loc[m, "end_date"] = camps["end_date"].max()
    camps.loc[m, "start_date"] = camps["start_date"].min()
    return target


def answer_key(cfg: dict, paused_brand: str) -> pd.DataFrame:
    start = pd.Timestamp(cfg["calendar"]["start_date"])
    n_weeks = cfg["calendar"]["weeks"]
    rows = []
    for a in cfg["anomalies"]:
        ws = start + pd.Timedelta(weeks=a["week"] - 1)
        if "days" in a:
            s, e = ws + pd.Timedelta(days=min(a["days"])), ws + pd.Timedelta(days=max(a["days"]))
        elif "day" in a:
            s = e = ws + pd.Timedelta(days=a["day"])
        else:
            wa = min(a.get("weeks_active", 1), n_weeks - a["week"] + 1)
            s, e = ws, ws + pd.Timedelta(weeks=wa) - pd.Timedelta(days=1)
        title, moves, spot = DESCRIPTIONS[a["id"]]
        scope = {"A1": "food_listing / android / position 1", "A2": f"advertiser {paused_brand} (snacks)",
                 "A3": "home_banner", "A4": "all zones", "A5": f"zone {a.get('zone_id', '')}",
                 "A6": "click event log only", "A7": "all"}[a["id"]]
        rows.append({"anomaly_id": a["id"], "week": a["week"], "start_date": s.date(), "end_date": e.date(),
                     "event": title, "scope": scope, "what_should_move": moves, "how_to_spot": spot,
                     "is_data_issue": a["id"] == "A6"})
    return pd.DataFrame(rows)
