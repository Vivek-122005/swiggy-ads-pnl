select
    cast(billing_line_id as {{ dbt.type_string() }}) as billing_line_id,
    cast(billing_date as date)                        as billing_date,
    cast(zone_id as {{ dbt.type_string() }})          as zone_id,
    cast(surface as {{ dbt.type_string() }})          as surface,
    cast(position as {{ dbt.type_int() }})            as slot_position,
    cast(campaign_id as {{ dbt.type_string() }})      as campaign_id,
    cast(billing_type as {{ dbt.type_string() }})     as billing_type,
    cast(billed_units as {{ dbt.type_bigint() }})     as billed_units,   -- clicks (CPC) or impressions (CPM)
    cast(gross_amount as {{ float_type() }})          as gross_amount
from {{ source('raw', 'raw_billing') }}
