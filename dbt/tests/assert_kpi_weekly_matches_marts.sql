-- The dashboard and the WBR must show the same number: kpi_weekly revenue/clicks/impressions
-- equal the fact table summed by week.
with f as (
    select d.week_start, sum(f.gross_revenue) as rev, sum(f.clicks) as clicks, sum(f.impressions) as imps
    from {{ ref('fct_ads_daily') }} f join {{ ref('dim_date') }} d on d.date_day = f.event_date
    group by 1
),
k as (
    select week_start,
           max(case when metric = 'ad_revenue' then value end)  as rev,
           max(case when metric = 'clicks' then value end)      as clicks,
           max(case when metric = 'impressions' then value end) as imps
    from {{ ref('kpi_weekly') }} where product = 'all' group by 1
)
select f.week_start, f.rev, k.rev as kpi_rev, f.clicks, k.clicks as kpi_clicks, f.imps, k.imps as kpi_imps
from f left join k using (week_start)
where k.week_start is null or abs(f.rev - k.rev) > 0.01 or f.clicks <> k.clicks or f.imps <> k.imps
