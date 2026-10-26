-- 'all' roll-ups in the KPI cube equal the sum of their parts (no double counting in any slice).
with parts as (
    select week_start, sum(gross_revenue) as rev, sum(clicks) as clicks
    from {{ ref('rpt_kpi_cube_weekly') }}
    where surface <> 'all' and zone_id <> 'all' and advertiser_segment <> 'all'
    group by 1
),
total as (
    select week_start, gross_revenue as rev, clicks
    from {{ ref('rpt_kpi_cube_weekly') }}
    where surface = 'all' and zone_id = 'all' and advertiser_segment = 'all'
)
select * from parts p join total t using (week_start)
where abs(p.rev - t.rev) > 0.01 or p.clicks <> t.clicks
