"""Export the reporting marts to compact JSON for the hosted dashboard (GitHub Pages).

    python -m dashboard.export --db data/warehouse.duckdb --out dashboard/site/data

The dashboard reads ONLY these files, and these files contain ONLY mart / reporting tables:
no metric is computed in the browser, so every number matches kpi_weekly and the WBRs.
Each file is {"columns": [...], "rows": [[...], ...]} to keep payloads small.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path

MARTS = "marts"

EXPORTS = {
    # file name             : SQL against the warehouse
    "kpi_weekly": f"""
        select week_number, cast(week_start as varchar) as week_start, product, metric, metric_order,
               value, prior_week_value, wow_pct, four_week_avg, vs_4wk_pct
        from {MARTS}.kpi_weekly order by week_number, product, metric_order""",
    "metrics": f"""
        select distinct metric, metric_order, metric_label, unit, good_direction, is_jd_metric, definition
        from {MARTS}.kpi_weekly order by metric_order""",
    "kpi_cube": f"""
        select week_number, surface, zone_id, advertiser_segment,
               gross_revenue, net_revenue, impressions, clicks, cpc_clicks, cpc_revenue, billed_clicks,
               attributed_orders, attributed_gmv, active_advertisers, top10_revenue, median_spend,
               ad_requests, filled_requests, bidders_sum, reserve_binding_count, gov
        from {MARTS}.rpt_kpi_cube_weekly order by week_number""",
    "revenue_bridge": f"""
        select week_number, surface, revenue_prior, revenue_current, revenue_change,
               requests_effect, fill_effect, ctr_effect, price_effect, residual,
               requests_prior, requests_current, fill_prior, fill_current, ctr_prior, ctr_current,
               price_prior, price_current
        from {MARTS}.rpt_revenue_bridge order by week_number, surface""",
    "movers": f"""
        select week_number, mover_rank, metric, metric_label, unit, good_direction, value,
               four_week_avg, vs_4wk_pct, wow_pct
        from {MARTS}.rpt_biggest_movers order by week_number, mover_rank""",
    "zones": f"""
        select week_number, zone_id, zone_name, lat, lon, gross_revenue, impressions, clicks,
               attributed_orders, attributed_gmv, active_advertisers, ctr, cvr, roas, fill_rate,
               revenue_vs_4wk_pct
        from {MARTS}.rpt_zone_weekly order by week_number, zone_id""",
    "categories": f"""
        select week_number, advertiser_type, category, gross_revenue, impressions, clicks,
               attributed_orders, attributed_gmv, active_advertisers, ctr, cvr, roas, spend_vs_4wk_pct
        from {MARTS}.rpt_category_weekly order by week_number, advertiser_type, category""",
    "cohorts": f"""
        select cohort_week, weeks_since_first, cohort_size, active_advertisers, retention
        from {MARTS}.rpt_cohort_retention order by cohort_week, weeks_since_first""",
    "fill_heatmap": f"""
        select week_number, zone_id, event_hour,
               sum(ad_requests) as ad_requests, sum(filled_requests) as filled_requests,
               sum(filled_requests) * 1.0 / nullif(sum(ad_requests), 0) as fill_rate
        from {MARTS}.rpt_inventory_weekly group by 1, 2, 3 order by 1, 2, 3""",
    "inventory_surface": f"""
        select week_number, surface, request_category,
               sum(ad_requests) as ad_requests, sum(filled_requests) as filled_requests,
               sum(unfilled_requests) as unfilled_requests,
               sum(filled_requests) * 1.0 / nullif(sum(ad_requests), 0) as fill_rate,
               sum(bidders_sum) * 1.0 / nullif(sum(ad_requests), 0) as bid_density,
               sum(reserve_binding_count) * 1.0 / nullif(sum(filled_requests), 0) as reserve_binding_rate,
               sum(clearing_price_sum) * 1.0 / nullif(sum(filled_requests), 0) as avg_clearing_price
        from {MARTS}.rpt_inventory_weekly group by 1, 2, 3 order by 1, 2, 3""",
    "unfilled_premium": f"""
        select week_number, zone_id, surface, event_hour, unfilled_requests, ad_requests, fill_rate
        from {MARTS}.rpt_inventory_weekly
        where event_hour in (12, 13, 19, 20, 21) and request_category in ('food', 'home')
        order by week_number, unfilled_requests desc""",
    "clearing_price_dist": f"""
        select d.week_number, i.surface,
               floor(i.avg_clearing_price) as price_bucket, sum(i.filled_requests) as filled_requests
        from {MARTS}.fct_inventory_hourly i
        join {MARTS}.dim_date d on d.date_day = i.event_date
        where i.filled_requests > 0
        group by 1, 2, 3 order by 1, 2, 3""",
    "platform_weekly": f"""
        select d.week_number, p.surface, p.slot_position, p.platform,
               sum(p.impressions) as impressions, sum(p.clicks) as clicks,
               sum(p.attributed_orders) as attributed_orders
        from {MARTS}.fct_ads_platform_daily p
        join {MARTS}.dim_date d on d.date_day = p.event_date
        group by 1, 2, 3, 4 order by 1, 2, 3, 4""",
    "top_advertisers": f"""
        select week_number, spend_rank, advertiser_id, advertiser_name, advertiser_segment, category,
               gross_spend, prior_week_spend, spend_wow_pct, budget, budget_utilisation, roas, is_active
        from {MARTS}.rpt_top_advertisers_weekly order by week_number, spend_rank""",
    "advertiser_weekly_summary": f"""
        select week_number,
               sum(case when is_active then 1 else 0 end) as active,
               sum(case when is_new then 1 else 0 end) as new,
               sum(case when is_churned then 1 else 0 end) as churned,
               count(is_churned) < count(*) as churn_provisional
        from {MARTS}.fct_advertiser_weekly group by 1 order by 1""",
    "zones_dim": f"select zone_id, zone_name, lat, lon from {MARTS}.dim_zone order by zone_id",
    "weeks": f"""
        select week_number, cast(min(date_day) as varchar) as week_start, cast(max(date_day) as varchar) as week_end
        from {MARTS}.dim_date group by 1 order by 1""",
}


def _clean(v):
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, 6)
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()
    if hasattr(v, "item"):          # numpy / decimal scalars
        return _clean(v.item())
    return v


# Tables also published as CSV, for Google Sheets (IMPORTDATA) and Data Studio. Same rows as the JSON.
CSV_EXPORTS = ["kpi_weekly", "kpi_cube", "revenue_bridge", "movers", "zones", "categories", "cohorts",
               "inventory_surface", "platform_weekly", "top_advertisers", "advertiser_weekly_summary", "weeks", "metrics"]

# Wide weekly KPI table for BI tools: one row per week x product, four columns per metric
# (value, prior week, WoW %, 4-week avg). Still read straight from kpi_weekly - nothing recomputed.
WIDE_SQL = f"""
    select k.week_number, cast(k.week_start as varchar) as week_start, k.product, k.metric,
           k.value, k.prior_week_value, k.wow_pct, k.four_week_avg
    from {MARTS}.kpi_weekly k order by 1, 3"""


def _write_csv(path: Path, cols: list[str], rows: list[list]) -> None:
    import csv
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)


def export(db: str, out: Path) -> None:
    import duckdb
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(db, read_only=True)
    for name, sql in EXPORTS.items():
        cur = con.execute(sql)
        cols = [c[0] for c in cur.description]
        rows = [[_clean(v) for v in r] for r in cur.fetchall()]
        (out / f"{name}.json").write_text(json.dumps({"columns": cols, "rows": rows}, separators=(",", ":")))
        if name in CSV_EXPORTS:
            _write_csv(out / f"{name}.csv", cols, rows)
        print(f"  {name:<28} {len(rows):>8,} rows")
    # wide KPI table (CSV only)
    long = con.execute(WIDE_SQL).fetchall()
    metrics = [r[0] for r in con.execute(f"select distinct metric, metric_order from {MARTS}.kpi_weekly order by 2").fetchall()]
    wide: dict = {}
    for wk, ws, prod, m, v, pv, wow, a4 in long:
        row = wide.setdefault((wk, prod), {"week_number": wk, "week_start": ws, "product": prod})
        row[m], row[f"{m}_prior"], row[f"{m}_wow"], row[f"{m}_4wk"] = (_clean(v), _clean(pv), _clean(wow), _clean(a4))
    cols = ["week_number", "week_start", "product"] + [c for m in metrics for c in (m, f"{m}_prior", f"{m}_wow", f"{m}_4wk")]
    _write_csv(out / "kpi_weekly_wide.csv", cols, [[r.get(c) for c in cols] for r in wide.values()])
    print(f"  {'kpi_weekly_wide (csv)':<28} {len(wide):>8,} rows")
    meta = {
        "refreshed_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d %H:%M IST"),
        "data_note": "ALL DATA IS SIMULATED. Restaurant and brand names come from public Kaggle datasets "
                     "(Zomato Bangalore, BigBasket); every ad metric attached to them is invented. Not Swiggy data.",
        "metric_dictionary_url": "https://vivek-122005.github.io/swiggy-ads-pnl/docs/",
        "repo_url": "https://github.com/Vivek-122005/swiggy-ads-pnl",
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/warehouse.duckdb")
    ap.add_argument("--out", default="dashboard/site/data")
    a = ap.parse_args()
    export(a.db, Path(a.out))


if __name__ == "__main__":
    main()
