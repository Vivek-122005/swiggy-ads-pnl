-- GRAIN: date x surface x position x platform. Serving-side drill-down (billing has no platform).
{% set keys = ['event_date', 'surface', 'slot_position', 'platform'] %}
with imp as (
    select event_date, surface, slot_position, platform, sum(impressions) as impressions
    from {{ ref('stg_impressions') }} group by 1, 2, 3, 4
),
clk as (
    select click_date as event_date, surface, slot_position, platform, count(*) as clicks
    from {{ ref('int_clicks_enriched') }} group by 1, 2, 3, 4
),
att as (
    select click_date as event_date, surface, slot_position, platform,
           count(*) as attributed_orders, sum(order_value) as attributed_gmv
    from {{ ref('int_attributed_orders') }} group by 1, 2, 3, 4
)
select
    {{ dbt_utils.generate_surrogate_key(keys) }} as platform_daily_key,
    imp.event_date, imp.surface, imp.slot_position, imp.platform,
    imp.impressions,
    coalesce(clk.clicks, 0)            as clicks,
    coalesce(att.attributed_orders, 0) as attributed_orders,
    coalesce(att.attributed_gmv, 0)    as attributed_gmv
from imp
{% for t in ['clk', 'att'] %}
left join {{ t }} on {% for c in keys %}{{ t }}.{{ c }} = imp.{{ c }}{% if not loop.last %} and {% endif %}{% endfor %}
{% endfor %}
