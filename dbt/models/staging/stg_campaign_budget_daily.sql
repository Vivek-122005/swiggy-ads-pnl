select
    cast(budget_date as date)                       as budget_date,
    cast(campaign_id as {{ dbt.type_string() }})    as campaign_id,
    cast(daily_budget as {{ float_type() }})        as daily_budget,
    cast(bid as {{ float_type() }})                 as bid,
    cast(status as {{ dbt.type_string() }})         as campaign_status
from {{ source('raw', 'raw_campaign_budget_daily') }}
