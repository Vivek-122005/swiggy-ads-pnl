-- GRAIN: week x product x zone x advertiser segment, with 'all' roll-ups for every combination,
-- so any dashboard filter reads a pre-computed row (distinct counts stay exact; nothing is
-- re-aggregated in the browser). kpi_weekly is the product x 'all' x 'all' slice of this table.
{% set dims = ['surface', 'zone_id', 'advertiser_segment'] %}
{% set combos = [[], ['surface'], ['zone_id'], ['advertiser_segment'], ['surface', 'zone_id'],
                 ['surface', 'advertiser_segment'], ['zone_id', 'advertiser_segment'], ['surface', 'zone_id', 'advertiser_segment']] %}
with ads as (
    select d.week_start, f.surface, f.zone_id, a.advertiser_segment, f.advertiser_id,
           sum(f.impressions) as impressions, sum(f.clicks) as clicks, sum(f.billed_clicks) as billed_clicks,
           sum(case when f.surface <> 'home_banner' then f.clicks else 0 end) as cpc_clicks,
           sum(f.gross_revenue) as gross_revenue, sum(f.net_revenue) as net_revenue,
           sum(f.cpc_revenue) as cpc_revenue, sum(f.cpm_revenue) as cpm_revenue,
           sum(f.attributed_orders) as attributed_orders, sum(f.attributed_gmv) as attributed_gmv
    from {{ ref('fct_ads_daily') }} f
    join {{ ref('dim_date') }} d on d.date_day = f.event_date
    join {{ ref('dim_advertiser') }} a using (advertiser_id)
    group by 1, 2, 3, 4, 5
),
adv_cells as (   -- advertiser spend inside each slice (for distinct counts, median, top-10)
    {% for c in combos %}
    select week_start,
           {% for d in dims %}{% if d in c %}{{ d }}{% else %}'all'{% endif %} as {{ d }}, {% endfor %}
           advertiser_id,
           sum(impressions) as impressions, sum(clicks) as clicks, sum(billed_clicks) as billed_clicks,
           sum(cpc_clicks) as cpc_clicks, sum(gross_revenue) as gross_revenue, sum(net_revenue) as net_revenue,
           sum(cpc_revenue) as cpc_revenue, sum(cpm_revenue) as cpm_revenue,
           sum(attributed_orders) as attributed_orders, sum(attributed_gmv) as attributed_gmv
    from ads
    group by week_start, {% for d in c %}{{ d }}, {% endfor %}advertiser_id
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
),
ranked as (
    select *,
           row_number() over (partition by week_start, surface, zone_id, advertiser_segment
                              order by gross_revenue desc, advertiser_id) as spend_rank
    from adv_cells
),
cells as (
    select week_start, surface, zone_id, advertiser_segment,
           sum(impressions) as impressions, sum(clicks) as clicks, sum(billed_clicks) as billed_clicks,
           sum(cpc_clicks) as cpc_clicks,
           sum(billed_clicks) - sum(cpc_clicks) as click_gap,
           sum(gross_revenue) as gross_revenue, sum(net_revenue) as net_revenue,
           sum(cpc_revenue) as cpc_revenue, sum(cpm_revenue) as cpm_revenue,
           sum(attributed_orders) as attributed_orders, sum(attributed_gmv) as attributed_gmv,
           sum(case when gross_revenue > 0 then 1 else 0 end) as active_advertisers,
           sum(case when spend_rank <= 10 then gross_revenue else 0 end) as top10_revenue
    from ranked
    group by 1, 2, 3, 4
),
medians as (
    select week_start, surface, zone_id, advertiser_segment, {{ median('gross_revenue') }} as median_spend
    from adv_cells where gross_revenue > 0
    group by 1, 2, 3, 4
),
inv_base as (
    select d.week_start, i.surface, i.zone_id,
           sum(i.ad_requests) as ad_requests, sum(i.filled_requests) as filled_requests,
           sum(i.bidders_sum) as bidders_sum, sum(i.reserve_binding_count) as reserve_binding_count
    from {{ ref('fct_inventory_hourly') }} i
    join {{ ref('dim_date') }} d on d.date_day = i.event_date
    group by 1, 2, 3
),
inv as (   -- inventory has no advertiser segment: only segment = 'all' rows get it
    {% for c in [[], ['surface'], ['zone_id'], ['surface', 'zone_id']] %}
    select week_start,
           {% for d in ['surface', 'zone_id'] %}{% if d in c %}{{ d }}{% else %}'all'{% endif %} as {{ d }}, {% endfor %}
           'all' as advertiser_segment,
           sum(ad_requests) as ad_requests, sum(filled_requests) as filled_requests,
           sum(bidders_sum) as bidders_sum, sum(reserve_binding_count) as reserve_binding_count
    from inv_base
    group by week_start{% for d in c %}, {{ d }}{% endfor %}
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
),
gov_base as (
    select d.week_start, p.zone_id, p.vertical, sum(p.gov) as gov
    from {{ ref('fct_platform_orders_daily') }} p
    join {{ ref('dim_date') }} d on d.date_day = p.order_date
    group by 1, 2, 3
),
surface_vertical as (
    select 'food_listing' as surface, 'food' as vertical union all
    select 'instamart_search', 'instamart' union all
    select 'home_banner', 'instamart'
),
gov as (   -- food listings monetise food GOV; Instamart search + banners monetise Instamart GOV
    select g.week_start, sv.surface, g.zone_id, g.gov
    from gov_base g join surface_vertical sv on sv.vertical = g.vertical
    union all
    select g.week_start, sv.surface, 'all', sum(g.gov)
    from gov_base g join surface_vertical sv on sv.vertical = g.vertical
    group by 1, 2
    union all
    select week_start, 'all', zone_id, sum(gov) from gov_base group by 1, 3
    union all
    select week_start, 'all', 'all', sum(gov) from gov_base group by 1
)
select
    {{ dbt_utils.generate_surrogate_key(['c.week_start', 'c.surface', 'c.zone_id', 'c.advertiser_segment']) }} as kpi_cube_key,
    c.week_start, dd.week_number, c.surface, c.zone_id, c.advertiser_segment,
    c.impressions, c.clicks, c.billed_clicks, c.cpc_clicks, c.click_gap,
    c.gross_revenue, c.net_revenue, c.cpc_revenue, c.cpm_revenue,
    c.attributed_orders, c.attributed_gmv, c.active_advertisers, c.top10_revenue, m.median_spend,
    i.ad_requests, i.filled_requests, i.bidders_sum, i.reserve_binding_count,
    gv.gov,
    case when gv.gov is not null then c.gross_revenue end as gross_revenue_with_gov
from cells c
join (select distinct week_start, week_number from {{ ref('dim_date') }}) dd on dd.week_start = c.week_start
left join medians m on m.week_start = c.week_start and m.surface = c.surface and m.zone_id = c.zone_id and m.advertiser_segment = c.advertiser_segment
left join inv i     on i.week_start = c.week_start and i.surface = c.surface and i.zone_id = c.zone_id and i.advertiser_segment = c.advertiser_segment
left join gov gv    on gv.week_start = c.week_start and gv.surface = c.surface and gv.zone_id = c.zone_id
                   and c.advertiser_segment = 'all'
