select
    cast(event_date as date)                        as event_date,
    cast(hour as {{ dbt.type_int() }})              as event_hour,
    cast(zone_id as {{ dbt.type_string() }})        as zone_id,
    cast(surface as {{ dbt.type_string() }})        as surface,
    cast(position as {{ dbt.type_int() }})          as slot_position,
    cast(platform as {{ dbt.type_string() }})       as platform,
    cast(campaign_id as {{ dbt.type_string() }})    as campaign_id,
    cast(impressions as {{ dbt.type_int() }})       as impressions
from {{ source('raw', 'raw_impressions') }}
