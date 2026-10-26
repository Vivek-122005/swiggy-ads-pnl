-- GRAIN: date x zone x vertical. All orders and GOV (ads + organic): the take-rate denominator.
select
    {{ dbt_utils.generate_surrogate_key(['order_date', 'zone_id', 'vertical']) }} as platform_orders_key,
    order_date, zone_id, vertical, sessions, orders, gov
from {{ ref('stg_platform_daily') }}
