"""Advertiser lifecycle: weekly budget changes and churn driven by ROAS and patience."""
from __future__ import annotations

import numpy as np
import pandas as pd


def weekly_update(cfg: dict, week: int, adv: pd.DataFrame, camps: pd.DataFrame,
                  spend_by_adv: pd.Series, gmv_by_adv: pd.Series, churned: np.ndarray,
                  rng: np.random.Generator) -> list[dict]:
    """Mutates camps['daily_budget'] and `churned` in place. Returns a change log."""
    lc = cfg["lifecycle"]
    log = []
    spend = spend_by_adv.reindex(adv["advertiser_id"]).fillna(0.0).to_numpy()
    gmv = gmv_by_adv.reindex(adv["advertiser_id"]).fillna(0.0).to_numpy()
    roas = np.where(spend > 0, gmv / np.maximum(spend, 1e-9), np.nan)
    patience = adv["patience"].to_numpy()
    adv_ids = adv["advertiser_id"].to_numpy()
    camp_adv_idx = camps["_adv_idx"].to_numpy()

    for i in np.flatnonzero((spend > 0) & ~churned):
        r = roas[i]
        p_churn = lc["base_churn_prob"]
        if r < lc["roas_churn_threshold"]:
            p_churn += (1 - patience[i]) * 0.10
        if rng.random() < p_churn:
            churned[i] = True
            log.append({"week": week, "advertiser_id": adv_ids[i], "action": "churn", "roas": round(float(r), 3)})
            continue
        # banners are fixed-term brand contracts: only CPC budgets react to weekly ROAS
        m = (camp_adv_idx == i) & (camps["billing_type"] == "CPC").to_numpy()
        if r < lc["roas_churn_threshold"]:
            camps.loc[m, "daily_budget"] *= (1 - lc["budget_down_pct"])
            log.append({"week": week, "advertiser_id": adv_ids[i], "action": "budget_down", "roas": round(float(r), 3)})
        elif r > lc["budget_up_roas"] and rng.random() < 0.65:
            camps.loc[m, "daily_budget"] *= (1 + lc["budget_up_pct"])
            log.append({"week": week, "advertiser_id": adv_ids[i], "action": "budget_up", "roas": round(float(r), 3)})
    return log
