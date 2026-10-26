-- GRAIN: date x zone x surface x position x advertiser.
-- Money comes from billing (source of truth); impressions/clicks from serving logs;
-- attributed orders/GMV from the last-click rule (booked on click date).
{% set keys = ['event_date', 'zone_id', 'surface', 'slot_position', 'advertiser_id'] %}
with imp as (
    select i.event_date, i.zone_id, i.surface, i.slot_position, c.advertiser_id, sum(i.impressions) as impressions
    from {{ ref('stg_impressions') }} i join {{ ref('stg_campaigns') }} c using (campaign_id)
    group by 1, 2, 3, 4, 5
),
clk as (
    select click_date as event_date, zone_id, surface, slot_position, advertiser_id, count(*) as clicks
    from {{ ref('int_clicks_enriched') }}
    group by 1, 2, 3, 4, 5
),
bill as (
    select billing_date as event_date, zone_id, surface, slot_position, advertiser_id,
           sum(case when billing_type = 'CPC' then billed_units else 0 end) as billed_clicks,
           sum(case when billing_type = 'CPM' then billed_units else 0 end) as billed_impressions,
           sum(gross_amount) as gross_revenue,
           sum(case when billing_type = 'CPC' then gross_amount else 0 end) as cpc_revenue,
           sum(case when billing_type = 'CPM' then gross_amount else 0 end) as cpm_revenue,
           sum(credit_amount) as credits,
           sum(net_amount) as net_revenue
    from {{ ref('int_billing_net') }}
    group by 1, 2, 3, 4, 5
),
att as (
    select click_date as event_date, zone_id, surface, slot_position, advertiser_id,
           count(*) as attributed_orders, sum(order_value) as attributed_gmv
    from {{ ref('int_attributed_orders') }}
    group by 1, 2, 3, 4, 5
),
keys as (
    select {{ keys | join(', ') }} from imp
    union distinct select {{ keys | join(', ') }} from clk
    union distinct select {{ keys | join(', ') }} from bill
    union distinct select {{ keys | join(', ') }} from att
)
select
    {{ dbt_utils.generate_surrogate_key(keys) }} as ads_daily_key,
    k.event_date, k.zone_id, k.surface, k.slot_position, k.advertiser_id,
    coalesce(imp.impressions, 0)        as impressions,
    coalesce(clk.clicks, 0)             as clicks,
    coalesce(bill.billed_clicks, 0)     as billed_clicks,
    coalesce(bill.billed_impressions, 0) as billed_impressions,
    coalesce(bill.gross_revenue, 0)     as gross_revenue,
    coalesce(bill.cpc_revenue, 0)       as cpc_revenue,
    coalesce(bill.cpm_revenue, 0)       as cpm_revenue,
    coalesce(bill.credits, 0)           as credits,
    coalesce(bill.net_revenue, 0)       as net_revenue,
    coalesce(att.attributed_orders, 0)  as attributed_orders,
    coalesce(att.attributed_gmv, 0)     as attributed_gmv
from keys k
{% for t in ['imp', 'clk', 'bill', 'att'] %}
left join {{ t }} on {% for c in keys %}{{ t }}.{{ c }} = k.{{ c }}{% if not loop.last %} and {% endif %}{% endfor %}
{% endfor %}
