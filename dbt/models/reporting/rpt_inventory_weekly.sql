-- Inventory health by week x zone x hour x surface x category: fill heatmap, bid density, reserve binding, clearing price.
select
    {{ dbt_utils.generate_surrogate_key(['d.week_start', 'i.zone_id', 'i.event_hour', 'i.surface', 'i.request_category']) }} as inventory_week_key,
    d.week_start, d.week_number, i.zone_id, i.event_hour, i.surface, i.request_category,
    sum(i.ad_requests) as ad_requests, sum(i.filled_requests) as filled_requests,
    sum(i.unfilled_requests) as unfilled_requests, sum(i.bidders_sum) as bidders_sum,
    sum(i.reserve_binding_count) as reserve_binding_count, sum(i.clearing_price_sum) as clearing_price_sum,
    {{ safe_divide('sum(i.filled_requests)', 'sum(i.ad_requests)') }}             as fill_rate,
    {{ safe_divide('sum(i.bidders_sum)', 'sum(i.ad_requests)') }}                 as bid_density,
    {{ safe_divide('sum(i.reserve_binding_count)', 'sum(i.filled_requests)') }}   as reserve_binding_rate,
    {{ safe_divide('sum(i.clearing_price_sum)', 'sum(i.filled_requests)') }}      as avg_clearing_price
from {{ ref('fct_inventory_hourly') }} i
join {{ ref('dim_date') }} d on d.date_day = i.event_date
group by 2, 3, 4, 5, 6, 7
