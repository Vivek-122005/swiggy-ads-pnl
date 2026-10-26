select
    cast(campaign_id as {{ dbt.type_string() }})   as campaign_id,
    cast(advertiser_id as {{ dbt.type_string() }}) as advertiser_id,
    cast(product as {{ dbt.type_string() }})       as surface,       -- food_listing | instamart_search | home_banner
    cast(billing_type as {{ dbt.type_string() }})  as billing_type,  -- CPC | CPM
    cast(target_zones as {{ dbt.type_string() }})  as target_zones,
    cast(start_date as date)                        as start_date,
    cast(end_date as date)                          as end_date,
    cast(initial_daily_budget as {{ float_type() }}) as initial_daily_budget,
    cast(bid as {{ float_type() }})                as initial_bid,
    cast(category as {{ dbt.type_string() }})      as category
from {{ source('raw', 'raw_campaigns') }}
