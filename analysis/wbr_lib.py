"""Helpers for the weekly business review (WBR) investigations.

Every number comes from the dbt marts (the same tables the dashboard reads), so the memo and the
dashboard always agree. Investigation order follows the playbook in the project plan:
check the data first -> revenue bridge -> mix vs rate -> drill down one dimension at a time ->
find where the change concentrates -> match it to an event -> quantify -> recommend.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parents[1] / "data" / "warehouse.duckdb"
JD_METRICS = ["ad_revenue", "ecpm", "ctr", "fill_rate", "active_advertisers", "roas"]


def con(db: str | Path = DB):
    import duckdb
    return duckdb.connect(str(db), read_only=True)


def q(sql: str, db: str | Path = DB) -> pd.DataFrame:
    with con(db) as c:
        return c.execute(sql).df()


# ------------------------------------------------------------------ formatting
def inr(x: float) -> str:
    """Indian-style rupee formatting: lakh / crore for large amounts."""
    if pd.isna(x):
        return "-"
    a = abs(x)
    if a >= 1e7:
        return f"₹{x / 1e7:.2f} Cr"
    if a >= 1e5:
        return f"₹{x / 1e5:.2f} L"
    return f"₹{x:,.0f}"


def fmt(value: float, unit: str) -> str:
    if pd.isna(value):
        return "-"
    return {"inr": inr(value), "pct": f"{value:.2%}", "x": f"{value:.2f}x",
            "ratio": f"{value:.1f}", "count": f"{value:,.0f}"}.get(unit, f"{value:,.2f}")


def pct(x: float) -> str:
    return "-" if pd.isna(x) else f"{x:+.1%}"


# ------------------------------------------------------------------ 1. data checks
def data_checks(week: int, db=DB) -> pd.DataFrame:
    """Pipeline sanity for the week: day completeness, billed vs logged clicks, reconciliation."""
    return q(f"""
        with d as (select date_day from marts.dim_date where week_number = {week}),
        billed as (select billing_date as day, sum(billed_units) as billed_clicks, sum(gross_amount) as billed_revenue
                   from staging.stg_billing where billing_type = 'CPC' group by 1),
        logged as (select click_date as day, count(*) as logged_clicks
                   from intermediate.int_clicks_enriched where billing_type = 'CPC' group by 1),
        mart as (select event_date as day, sum(cpc_revenue) as mart_cpc_revenue, sum(impressions) as impressions,
                        sum(attributed_orders) as attributed_orders
                 from marts.fct_ads_daily group by 1),
        plat as (select order_date as day, sum(orders) as platform_orders from marts.fct_platform_orders_daily group by 1)
        select d.date_day, b.billed_clicks, l.logged_clicks,
               (b.billed_clicks - l.logged_clicks) * 1.0 / b.billed_clicks as click_log_gap,
               b.billed_revenue, m.mart_cpc_revenue, m.impressions,
               l.logged_clicks * 1.0 / m.impressions as ctr_logged,
               b.billed_clicks * 1.0 / m.impressions as ctr_billed,
               m.attributed_orders, p.platform_orders,
               p.platform_orders * 1000.0 / m.impressions as platform_orders_per_1k_imps
        from d left join billed b on b.day = d.date_day left join logged l on l.day = d.date_day
        left join mart m on m.day = d.date_day left join plat p on p.day = d.date_day
        order by 1""", db)


# ------------------------------------------------------------------ 2. scorecard
def scorecard(week: int, product: str = "all", db=DB) -> pd.DataFrame:
    df = q(f"""
        select metric, metric_label, unit, good_direction, value, prior_week_value, wow_pct, four_week_avg, vs_4wk_pct
        from marts.kpi_weekly where week_number = {week} and product = '{product}' order by metric_order""", db)
    return df


def scorecard_table(week: int, metrics=JD_METRICS, db=DB) -> pd.DataFrame:
    s = scorecard(week, db=db).set_index("metric").loc[metrics]
    return pd.DataFrame({
        "Metric": s["metric_label"],
        "This week": [fmt(v, u) for v, u in zip(s["value"], s["unit"])],
        "Last week": [fmt(v, u) for v, u in zip(s["prior_week_value"], s["unit"])],
        "WoW": [pct(x) for x in s["wow_pct"]],
        "4-wk avg": [fmt(v, u) for v, u in zip(s["four_week_avg"], s["unit"])],
        "vs 4-wk": [pct(x) for x in s["vs_4wk_pct"]],
    }).reset_index(drop=True)


def trend(metric: str, product: str = "all", db=DB) -> pd.DataFrame:
    return q(f"""select week_number, value, four_week_avg from marts.kpi_weekly
                 where metric = '{metric}' and product = '{product}' order by week_number""", db)


# ------------------------------------------------------------------ 3. revenue bridge
def bridge(week: int, db=DB) -> pd.DataFrame:
    return q(f"""select surface, revenue_prior, requests_effect, fill_effect, ctr_effect, price_effect,
                        revenue_current, revenue_change, residual
                 from marts.rpt_revenue_bridge where week_number = {week}
                 order by case surface when 'all' then 0 else 1 end, surface""", db)


# ------------------------------------------------------------------ 4. mix vs rate
def mix_rate(df: pd.DataFrame, segment_cols: list[str], num: str = "clicks", den: str = "impressions",
             week_col: str = "week_number", w0: int | None = None, w1: int | None = None) -> pd.DataFrame:
    """Split the change in a ratio (default CTR) into mix and rate effects across segments i.

        dCTR = sum_i (s_i^1 - s_i^0) * CTR_i^0   [mix]   +   sum_i s_i^1 * (CTR_i^1 - CTR_i^0)   [rate]

    where s_i is segment i's share of the denominator. Returns one row per segment with its
    contribution to each effect, sorted by |rate contribution|.
    """
    g = df.groupby([week_col] + segment_cols, as_index=False)[[num, den]].sum()
    a = g[g[week_col] == w0].set_index(segment_cols)
    b = g[g[week_col] == w1].set_index(segment_cols)
    idx = a.index.union(b.index)
    a, b = a.reindex(idx).fillna(0), b.reindex(idx).fillna(0)
    s0, s1 = a[den] / a[den].sum(), b[den] / b[den].sum()
    r0 = (a[num] / a[den]).fillna(0)
    r1 = (b[num] / b[den]).fillna(0)
    out = pd.DataFrame({"share_prior": s0, "share_current": s1, "rate_prior": r0, "rate_current": r1,
                        "mix_effect": (s1 - s0) * r0, "rate_effect": s1 * (r1 - r0)})
    out["total_effect"] = out["mix_effect"] + out["rate_effect"]
    out["share_of_change"] = out["total_effect"] / out["total_effect"].sum()
    out = out.reindex(out["rate_effect"].abs().sort_values(ascending=False).index)
    out.attrs.update(total_prior=a[num].sum() / a[den].sum(), total_current=b[num].sum() / b[den].sum(),
                     mix=out["mix_effect"].sum(), rate=out["rate_effect"].sum())
    return out


def platform_slots(weeks: tuple[int, ...], surface: str | None = None, db=DB) -> pd.DataFrame:
    w = ",".join(str(x) for x in weeks)
    s = f"and p.surface = '{surface}'" if surface else ""
    return q(f"""select d.week_number, p.surface, p.slot_position, p.platform,
                        sum(p.impressions) as impressions, sum(p.clicks) as clicks,
                        sum(p.attributed_orders) as attributed_orders
                 from marts.fct_ads_platform_daily p join marts.dim_date d on d.date_day = p.event_date
                 where d.week_number in ({w}) {s}
                 group by 1, 2, 3, 4""", db)


# ------------------------------------------------------------------ 5. drill-downs
def by_dimension(weeks: tuple[int, ...], dim: str, db=DB) -> pd.DataFrame:
    """Revenue, impressions, clicks and attributed orders by one dimension of fct_ads_daily
    (zone_id, surface, slot_position, advertiser_segment, category, advertiser_id)."""
    w = ",".join(str(x) for x in weeks)
    col = {"advertiser_segment": "a.advertiser_segment", "category": "a.category",
           "advertiser_id": "a.advertiser_id"}.get(dim, f"f.{dim}")
    return q(f"""select d.week_number, {col} as {dim},
                        sum(f.gross_revenue) as gross_revenue, sum(f.impressions) as impressions,
                        sum(f.clicks) as clicks, sum(f.attributed_orders) as attributed_orders,
                        sum(f.attributed_gmv) as attributed_gmv
                 from marts.fct_ads_daily f
                 join marts.dim_date d on d.date_day = f.event_date
                 join marts.dim_advertiser a on a.advertiser_id = f.advertiser_id
                 where d.week_number in ({w})
                 group by 1, 2""", db)


def concentration(df: pd.DataFrame, dim: str, value: str, w0: int, w1: int) -> pd.DataFrame:
    """Where does the change in `value` concentrate? Share of the total change by segment."""
    p = df.pivot_table(index=dim, columns="week_number", values=value, aggfunc="sum").fillna(0)
    p["change"] = p[w1] - p[w0]
    p["share_of_change"] = p["change"] / p["change"].sum()
    return p.sort_values("change", key=abs, ascending=False)


def advertiser_moves(w0: int, w1: int, n: int = 10, db=DB) -> pd.DataFrame:
    return q(f"""
        with w as (
            select f.advertiser_id, a.advertiser_name, a.advertiser_segment, a.category,
                   sum(case when f.week_number = {w0} then f.gross_spend else 0 end) as spend_prior,
                   sum(case when f.week_number = {w1} then f.gross_spend else 0 end) as spend_current,
                   max(case when f.week_number = {w1} then f.budget_utilisation end)  as budget_util_current,
                   max(case when f.week_number = {w0} then f.roas end)                as roas_prior
            from marts.fct_advertiser_weekly f join marts.dim_advertiser a using (advertiser_id)
            where f.week_number in ({w0}, {w1})
            group by 1, 2, 3, 4)
        select *, spend_current - spend_prior as spend_change from w
        order by abs(spend_current - spend_prior) desc limit {n}""", db)


def inventory(weeks: tuple[int, ...], surface: str | None = None, db=DB) -> pd.DataFrame:
    w = ",".join(str(x) for x in weeks)
    s = f"and surface = '{surface}'" if surface else ""
    return q(f"""select week_number, surface, request_category,
                        sum(ad_requests) as ad_requests, sum(filled_requests) as filled_requests,
                        sum(filled_requests) * 1.0 / sum(ad_requests) as fill_rate,
                        sum(bidders_sum) * 1.0 / sum(ad_requests) as bid_density,
                        sum(reserve_binding_count) * 1.0 / nullif(sum(filled_requests), 0) as reserve_binding_rate,
                        sum(clearing_price_sum) / nullif(sum(filled_requests), 0) as avg_clearing_price
                 from marts.rpt_inventory_weekly where week_number in ({w}) {s}
                 group by 1, 2, 3 order by 2, 3, 1""", db)


def zone_week(weeks: tuple[int, ...], db=DB) -> pd.DataFrame:
    w = ",".join(str(x) for x in weeks)
    return q(f"""select week_number, zone_id, zone_name, gross_revenue, clicks, impressions, attributed_orders,
                        ctr, cvr, roas, fill_rate
                 from marts.rpt_zone_weekly where week_number in ({w}) order by zone_id, week_number""", db)
