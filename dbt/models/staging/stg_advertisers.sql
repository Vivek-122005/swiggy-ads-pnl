select
    cast(advertiser_id as {{ dbt.type_string() }})   as advertiser_id,
    cast(advertiser_name as {{ dbt.type_string() }}) as advertiser_name,
    cast(advertiser_type as {{ dbt.type_string() }}) as advertiser_type,   -- restaurant | brand
    cast(segment as {{ dbt.type_string() }})         as advertiser_segment, -- chain | independent | brand
    cast(is_chain as boolean)                         as is_chain,
    cast(category as {{ dbt.type_string() }})        as category,          -- cuisine for restaurants, Instamart category for brands
    cast(home_zone as {{ dbt.type_string() }})       as home_zone_id,
    cast(rating as {{ float_type() }})               as rating,
    cast(cost_for_two as {{ float_type() }})         as price_reference,   -- cost for two / avg basket value
    cast(joined_on as date)                          as joined_on,
    cast(name_source as {{ dbt.type_string() }})     as name_source
from {{ source('raw', 'raw_advertisers') }}
