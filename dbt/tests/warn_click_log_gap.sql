{{ config(severity = 'warn') }}
-- Billed CPC clicks vs valid logged CPC clicks by day. They should match; a gap means the click
-- log lost events (a DATA problem) - check before explaining a CTR drop as a business change.
with billed as (
    select billing_date as d, sum(billed_units) as billed from {{ ref('stg_billing') }} where billing_type = 'CPC' group by 1
),
logged as (
    select click_date as d, count(*) as logged from {{ ref('int_clicks_enriched') }} where billing_type = 'CPC' group by 1
)
select b.d as event_date, b.billed, l.logged, (b.billed - l.logged) * 1.0 / b.billed as gap
from billed b join logged l using (d)
where abs(b.billed - l.logged) * 1.0 / b.billed > {{ var('click_log_gap_warn') }}
