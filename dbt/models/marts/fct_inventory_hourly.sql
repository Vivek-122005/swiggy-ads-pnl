-- GRAIN: date x hour x zone x surface x request category x position (platforms summed).
select
    {{ dbt_utils.generate_surrogate_key(['event_date', 'event_hour', 'zone_id', 'surface', 'request_category', 'slot_position']) }} as inventory_hourly_key,
    event_date, event_hour, zone_id, surface, request_category, slot_position,
    sum(ad_requests)          as ad_requests,
    sum(filled_requests)      as filled_requests,
    sum(unfilled_requests)    as unfilled_requests,
    sum(bidders_sum)          as bidders_sum,
    sum(reserve_bound_count)  as reserve_binding_count,
    sum(clearing_price_sum)   as clearing_price_sum,
    {{ safe_divide('sum(filled_requests)', 'sum(ad_requests)') }}      as fill_rate,
    {{ safe_divide('sum(bidders_sum)', 'sum(ad_requests)') }}          as avg_bidders,
    {{ safe_divide('sum(clearing_price_sum)', 'sum(filled_requests)') }} as avg_clearing_price
from {{ ref('int_auction_outcomes') }}
group by 2, 3, 4, 5, 6, 7
