select
    cast(order_id as {{ dbt.type_string() }})      as order_id,
    {{ to_ts('order_ts') }}                         as order_ts,
    cast(order_ts as date)                          as order_date,
    cast(user_id as {{ dbt.type_bigint() }})        as user_id,
    cast(advertiser_id as {{ dbt.type_string() }})  as advertiser_id,
    cast(zone_id as {{ dbt.type_string() }})        as zone_id,
    cast(vertical as {{ dbt.type_string() }})       as vertical,
    cast(order_value as {{ float_type() }})         as order_value
from {{ source('raw', 'raw_orders') }}
