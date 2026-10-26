-- The 3 metrics (overall, product = 'all') that moved most against their 4-week baseline each week,
-- auto-flagged on the executive page.
-- Score = |% vs 4-week avg| / that metric's own typical move (std-dev of its % vs 4-week avg over the
-- previous 8 weeks, floored at 1%), so naturally noisy small counts don't crowd out real moves.
-- The data-quality metric click_log_gap is ~0 when healthy, so it is scored on its level instead.
with base as (
    select week_start, week_number, metric, metric_label, unit, good_direction, value, prior_week_value,
           wow_pct, four_week_avg, vs_4wk_pct,
           case when count(vs_4wk_pct) over (partition by metric order by week_number
                                             rows between 8 preceding and 1 preceding) >= 3
                then stddev_samp(vs_4wk_pct) over (partition by metric order by week_number
                                                   rows between 8 preceding and 1 preceding) end as typical_move
    from {{ ref('kpi_weekly') }}
    where product = 'all'
      and metric not in ('net_ad_revenue', 'attributed_gmv', 'impressions', 'clicks', 'attributed_orders',
                         'median_spend', 'churned_advertisers')
),
scored as (
    select *,
           case when metric = 'click_log_gap' then abs(value) / 0.002
                else abs(vs_4wk_pct) / greatest(coalesce(typical_move, 0.05), 0.01) end as move_score
    from base
    where four_week_avg is not null or metric = 'click_log_gap'
),
ranked as (
    select *, row_number() over (partition by week_start order by move_score desc, metric) as mover_rank
    from scored
    where move_score is not null
)
select {{ dbt_utils.generate_surrogate_key(['week_start', 'metric']) }} as mover_key, *
from ranked
where mover_rank <= 3
