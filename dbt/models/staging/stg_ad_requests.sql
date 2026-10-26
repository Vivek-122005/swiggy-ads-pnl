select
    cast(event_date as date)                        as event_date,
    cast(hour as {{ dbt.type_int() }})              as event_hour,
    cast(zone_id as {{ dbt.type_string() }})        as zone_id,
    cast(surface as {{ dbt.type_string() }})        as surface,
    cast(category as {{ dbt.type_string() }})       as request_category,   -- Instamart search category; 'food' / 'home' otherwise
    cast(position as {{ dbt.type_int() }})          as slot_position,
    cast(platform as {{ dbt.type_string() }})       as platform,
    cast(ad_requests as {{ dbt.type_int() }})       as ad_requests,
    cast(filled_requests as {{ dbt.type_int() }})   as filled_requests,
    cast(bidders_sum as {{ dbt.type_int() }})       as bidders_sum,
    cast(reserve_bound_count as {{ dbt.type_int() }}) as reserve_bound_count,
    cast(clearing_price_sum as {{ float_type() }})  as clearing_price_sum
from {{ source('raw', 'raw_ad_requests') }}
