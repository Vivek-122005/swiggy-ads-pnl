-- Gross billed revenue less credits. Credits are booked against the ORIGINAL billing date
-- (restated), so net revenue for a past week can move when a late credit lands.
with credits as (
    select billing_line_id, sum(credit_amount) as credit_amount
    from {{ ref('stg_billing_adjustments') }}
    group by 1
)
select
    b.billing_line_id, b.billing_date, b.zone_id, b.surface, b.slot_position, b.campaign_id,
    c.advertiser_id, b.billing_type, b.billed_units,
    b.gross_amount,
    coalesce(cr.credit_amount, 0)                         as credit_amount,
    b.gross_amount - coalesce(cr.credit_amount, 0)        as net_amount
from {{ ref('stg_billing') }} b
join {{ ref('stg_campaigns') }} c using (campaign_id)
left join credits cr using (billing_line_id)
