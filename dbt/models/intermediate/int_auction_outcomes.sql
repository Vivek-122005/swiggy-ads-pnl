-- Every ad request is an auction: it ends with a paid winner (filled) or an unfilled slot.
select
    event_date, event_hour, zone_id, surface, request_category, slot_position, platform,
    ad_requests,
    filled_requests,
    ad_requests - filled_requests            as unfilled_requests,
    bidders_sum,                             -- sum over auctions of eligible bidders
    reserve_bound_count,                     -- filled auctions priced by the reserve
    clearing_price_sum                       -- sum of clearing prices (CPC in INR, CPM in INR for banners)
from {{ ref('stg_ad_requests') }}
