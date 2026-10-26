-- clicks <= impressions <= ad requests, for every row at the slot-day grain.
with ads as (
    select event_date, zone_id, surface, slot_position, sum(impressions) as impressions, sum(clicks) as clicks
    from {{ ref('fct_ads_daily') }} group by 1, 2, 3, 4
),
inv as (
    select event_date, zone_id, surface, slot_position, sum(ad_requests) as ad_requests, sum(filled_requests) as filled
    from {{ ref('fct_inventory_hourly') }} group by 1, 2, 3, 4
)
select a.*, i.ad_requests, i.filled
from ads a
left join inv i using (event_date, zone_id, surface, slot_position)
where a.clicks > a.impressions
   or a.impressions > coalesce(i.ad_requests, 0)
   or a.impressions <> coalesce(i.filled, 0)          -- every filled request is exactly one impression
