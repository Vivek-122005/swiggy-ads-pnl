-- Net = gross - credits, and total credits equal the raw adjustments table.
select 'credits' as check_name, sum(credits) as mart, (select sum(credit_amount) from {{ source('raw', 'raw_billing_adjustments') }}) as raw
from {{ ref('fct_ads_daily') }}
having abs(sum(credits) - (select sum(credit_amount) from {{ source('raw', 'raw_billing_adjustments') }})) > 0.01
union all
select 'net_identity', sum(net_revenue), sum(gross_revenue - credits)
from {{ ref('fct_ads_daily') }}
having abs(sum(net_revenue) - sum(gross_revenue - credits)) > 0.01
