-- ATTRIBUTION RULE (metric dictionary): an order is ad-attributed if the same user clicked an ad of
-- the same advertiser within the previous var('attribution_window_hours') hours. Only the LAST such
-- click gets credit. Credit is booked on the CLICK date so spend and outcomes line up in time.
with candidates as (
    select
        o.order_id, o.order_ts, o.order_date, o.order_value, o.vertical,
        k.click_id, k.click_ts, k.click_date, k.campaign_id, k.advertiser_id,
        k.zone_id, k.surface, k.slot_position, k.platform,
        row_number() over (partition by o.order_id order by k.click_ts desc, k.click_id desc) as click_rank
    from {{ ref('stg_orders') }} o
    join {{ ref('int_clicks_enriched') }} k
      on  k.user_id = o.user_id
      and k.advertiser_id = o.advertiser_id
      and k.click_ts <= o.order_ts
      and o.order_ts <= {{ dbt.dateadd('hour', var('attribution_window_hours'), 'k.click_ts') }}
)

select
    order_id, order_ts, order_date, order_value, vertical,
    click_id, click_ts, click_date, campaign_id, advertiser_id,
    zone_id, surface, slot_position, platform,
    {{ dbt.datediff('click_ts', 'order_ts', 'minute') }} as minutes_click_to_order
from candidates
where click_rank = 1
