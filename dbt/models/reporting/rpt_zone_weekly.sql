-- Zones: where should sales focus? Revenue, ROAS, CTR, fill and spend growth by zone and week.
with z as (
    select c.week_start, c.week_number, c.zone_id, c.gross_revenue, c.impressions, c.clicks,
           c.attributed_orders, c.attributed_gmv, c.active_advertisers, c.ad_requests, c.filled_requests,
           c.billed_clicks, c.cpc_clicks
    from {{ ref('rpt_kpi_cube_weekly') }} c
    where c.surface = 'all' and c.advertiser_segment = 'all' and c.zone_id <> 'all'
)
select
    {{ dbt_utils.generate_surrogate_key(['z.week_start', 'z.zone_id']) }} as zone_week_key,
    z.week_start, z.week_number, z.zone_id, d.zone_name, d.lat, d.lon,
    z.gross_revenue, z.impressions, z.clicks, z.attributed_orders, z.attributed_gmv, z.active_advertisers,
    z.ad_requests, z.filled_requests,
    {{ safe_divide('z.clicks', 'z.impressions') }}                as ctr,
    {{ safe_divide('z.attributed_orders', 'z.clicks') }}          as cvr,
    {{ safe_divide('z.attributed_gmv', 'z.gross_revenue') }}      as roas,
    {{ safe_divide('z.filled_requests', 'z.ad_requests') }}       as fill_rate,
    {{ safe_divide('z.gross_revenue - avg(z.gross_revenue) over (partition by z.zone_id order by z.week_number rows between 4 preceding and 1 preceding)',
                   'avg(z.gross_revenue) over (partition by z.zone_id order by z.week_number rows between 4 preceding and 1 preceding)') }} as revenue_vs_4wk_pct
from z
join {{ ref('dim_zone') }} d using (zone_id)
