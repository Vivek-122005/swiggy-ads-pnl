"""Generate the WBR investigation notebooks (one per week investigated).

    python analysis/build_notebooks.py          # writes analysis/wbr_week_XX.ipynb

Each notebook follows the same playbook and reads only the dbt marts via wbr_lib, so the memo,
the notebook and the dashboard show the same numbers. CI executes them and publishes HTML.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

SETUP = """import sys, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
sys.path.insert(0, '.')
import wbr_lib as w
pd.set_option('display.float_format', lambda x: f'{x:,.4f}')
sns.set_theme(style='whitegrid')
WEEK, PRIOR = {week}, {week} - 1
print(f'WBR investigation: week {WEEK} vs week {PRIOR}  (ALL DATA SIMULATED)')"""

COMMON_HEAD = [
    ("md", "# WBR investigation — week {week}\n\n**Question:** {question}\n\n"
           "Playbook: check the data → revenue bridge → mix vs rate → drill down one dimension at a time → "
           "find where it concentrates → match to an event → quantify → recommend. All data is simulated."),
    ("code", SETUP),
    ("md", "## 1. Check the data first\nDays complete? Billed clicks vs logged clicks? Orders per impression steady?"),
    ("code", "dq = w.data_checks(WEEK)\ndq"),
    ("md", "## 2. Scorecard — the 6 JD metrics"),
    ("code", "w.scorecard_table(WEEK)"),
    ("code", "w.scorecard(WEEK)[['metric','value','prior_week_value','wow_pct','four_week_avg','vs_4wk_pct']]"),
    ("md", "## 3. Revenue bridge — which term of requests × fill × CTR × price moved?"),
    ("code", "br = w.bridge(WEEK)\nbr"),
]

SPECIFIC = {
    6: dict(question="Why did ad revenue and CTR fall this week?", cells=[
        ("md", "## 4. Mix or rate? CTR across surface × position × platform"),
        ("code", "ps = w.platform_slots((PRIOR, WEEK))\nmr = w.mix_rate(ps, ['surface', 'slot_position', 'platform'], w0=PRIOR, w1=WEEK)\n"
                 "print(f\"CTR {mr.attrs['total_prior']:.4%} -> {mr.attrs['total_current']:.4%}; mix {mr.attrs['mix']:+.5f}, rate {mr.attrs['rate']:+.5f}\")\nmr.head(8)"),
        ("md", "## 5. Drill down — food listings by platform and position"),
        ("code", "food = ps[ps.surface == 'food_listing'].assign(ctr=lambda d: d.clicks / d.impressions)\n"
                 "food.pivot_table(index=['platform', 'slot_position'], columns='week_number', values='ctr')"),
        ("code", "tr = w.platform_slots(tuple(range(1, 27)), 'food_listing')\n"
                 "tr = tr.assign(seg=lambda d: d.platform + ' p' + d.slot_position.astype(str)).groupby(['week_number','seg'])[['clicks','impressions']].sum()\n"
                 "ax = (tr.clicks / tr.impressions).unstack().plot(figsize=(11, 4), title='Food listings CTR by platform x position')\nax.axvspan(5.5, 7.5, alpha=.1)"),
        ("md", "## 6. Quantify — lost clicks × CPC"),
        ("code", "seg = food[(food.platform == 'android') & (food.slot_position == 1)].set_index('week_number')\n"
                 "base_ctr = seg.loc[PRIOR, 'clicks'] / seg.loc[PRIOR, 'impressions']\n"
                 "lost_clicks = base_ctr * seg.loc[WEEK, 'impressions'] - seg.loc[WEEK, 'clicks']\n"
                 "cpc = w.scorecard(WEEK, 'food_listing').set_index('metric').loc['cpc', 'value']\n"
                 "print(f'Lost clicks on Android slot 1: {lost_clicks:,.0f}; at CPC {w.inr(cpc)} = {w.inr(lost_clicks * cpc)} of revenue this week')"),
    ]),
    9: dict(question="Why did Instamart revenue and top-10 concentration drop?", cells=[
        ("md", "## 4. Which advertisers moved?"),
        ("code", "w.advertiser_moves(PRIOR, WEEK, n=10)"),
        ("md", "## 5. Drill down — Instamart inventory by category"),
        ("code", "inv = w.inventory((PRIOR, WEEK), 'instamart_search')\ninv.pivot_table(index='request_category', columns='week_number', values=['fill_rate', 'bid_density', 'avg_clearing_price'])"),
        ("code", "conc = w.scorecard(WEEK).set_index('metric').loc[['top10_concentration', 'active_advertisers', 'ad_revenue']]\nconc"),
        ("md", "## 6. Quantify"),
        ("code", "m = w.advertiser_moves(PRIOR, WEEK, n=1).iloc[0]\nprint(f\"{m.advertiser_name} ({m.category}): spend {w.inr(m.spend_prior)} -> {w.inr(m.spend_current)}; budget utilisation now {m.budget_util_current}\")"),
    ]),
    12: dict(question="Banner CPM jumped while banner revenue fell — what changed in the auction?", cells=[
        ("md", "## 4. Inventory and auction health — home banners"),
        ("code", "inv = w.inventory(tuple(range(PRIOR - 3, WEEK + 2)), 'home_banner')\ninv[['week_number','ad_requests','fill_rate','bid_density','reserve_binding_rate','avg_clearing_price']]"),
        ("code", "ax = inv.set_index('week_number')[['fill_rate','reserve_binding_rate']].plot(figsize=(9,3.5), marker='o', title='Home banners: fill vs reserve binding')"),
        ("md", "## 5. Bridge for banners only"),
        ("code", "br[br.surface == 'home_banner']"),
        ("md", "## 6. Quantify — revenue vs unsold inventory"),
        ("code", "b = inv.set_index('week_number')\nunsold = (b.loc[WEEK,'ad_requests'] * (b.loc[PRIOR,'fill_rate'] - b.loc[WEEK,'fill_rate']))\n"
                 "print(f'Extra unfilled banner requests vs last week: {unsold:,.0f}; at last week eCPM that inventory was worth ~{w.inr(unsold * b.loc[PRIOR, \"avg_clearing_price\"] / 1000)}')"),
    ]),
    15: dict(question="Revenue, sessions and orders jumped mid-week — is it real demand or a rate change?", cells=[
        ("code", "dq[['date_day','platform_orders','ctr_logged','platform_orders_per_1k_imps']]"),
        ("code", "z = w.zone_week((PRIOR, WEEK))\nz.pivot_table(index='zone_name', columns='week_number', values=['ctr','cvr','roas'])"),
    ]),
    21: dict(question="CTR rose but conversion fell — is something wrong in one zone?", cells=[
        ("code", "z = w.zone_week((PRIOR, WEEK))\nz.pivot_table(index='zone_name', columns='week_number', values=['clicks','ctr','cvr','attributed_orders'])"),
        ("code", "zz = w.by_dimension((PRIOR, WEEK), 'zone_id')\nw.concentration(zz, 'zone_id', 'clicks', PRIOR, WEEK).head(5)"),
    ]),
    24: dict(question="CTR dipped on one day — business problem or data problem?", cells=[
        ("md", "Data checks above: compare billed clicks (billing system) with logged clicks (event log) by day."),
        ("code", "dq[['date_day','billed_clicks','logged_clicks','click_log_gap','ctr_logged','ctr_billed','platform_orders_per_1k_imps']]"),
    ]),
    26: dict(question="Requests, bids and new advertisers all spiked — problem or season?", cells=[
        ("code", "w.scorecard(WEEK).set_index('metric').loc[['ad_requests','bid_density','cpc','new_advertisers','active_advertisers','ad_revenue']]"),
        ("code", "w.trend('new_advertisers')"),
    ]),
}


_ids = iter(range(10**6))


def cell(kind: str, src: str) -> dict:
    lines = src.splitlines(keepends=True)
    cid = f"c{next(_ids):04d}"
    if kind == "md":
        return {"id": cid, "cell_type": "markdown", "metadata": {}, "source": lines}
    return {"id": cid, "cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines}


def build(week: int, spec: dict) -> dict:
    cells = [cell(k, s.replace("{week}", str(week)).replace("{question}", spec["question"])) for k, s in COMMON_HEAD]
    cells += [cell(k, s) for k, s in spec["cells"]]
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                         "language_info": {"name": "python"}},
            "nbformat": 4, "nbformat_minor": 5}


def main():
    for week, spec in SPECIFIC.items():
        p = HERE / f"wbr_week_{week:02d}.ipynb"
        p.write_text(json.dumps(build(week, spec), indent=1))
        print("wrote", p.name)


if __name__ == "__main__":
    main()
