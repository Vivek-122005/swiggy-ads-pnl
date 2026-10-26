select
    cast(adjustment_id as {{ dbt.type_string() }})   as adjustment_id,
    cast(billing_line_id as {{ dbt.type_string() }}) as billing_line_id,
    cast(adjustment_date as date)                     as adjustment_date,
    cast(reason as {{ dbt.type_string() }})          as adjustment_reason,
    cast(credit_amount as {{ float_type() }})        as credit_amount
from {{ source('raw', 'raw_billing_adjustments') }}
