-- Reconciliation: revenue in the mart equals revenue in the raw billing table, per day and in total.
with mart as (select event_date, sum(gross_revenue) as rev from {{ ref('fct_ads_daily') }} group by 1),
     raw  as (select cast(billing_date as date) as event_date, sum(gross_amount) as rev from {{ source('raw', 'raw_billing') }} group by 1)
select coalesce(m.event_date, r.event_date) as event_date, m.rev as mart_revenue, r.rev as billing_revenue
from mart m full outer join raw r on m.event_date = r.event_date
where abs(coalesce(m.rev, 0) - coalesce(r.rev, 0)) > 0.01
