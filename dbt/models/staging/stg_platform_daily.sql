select
    cast(order_date as date)                        as order_date,
    cast(zone_id as {{ dbt.type_string() }})        as zone_id,
    cast(vertical as {{ dbt.type_string() }})       as vertical,
    cast(sessions as {{ dbt.type_bigint() }})       as sessions,
    cast(orders as {{ dbt.type_bigint() }})         as orders,
    cast(gov as {{ float_type() }})                 as gov
from {{ source('raw', 'raw_platform_daily') }}
