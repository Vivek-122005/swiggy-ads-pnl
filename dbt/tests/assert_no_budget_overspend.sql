-- No advertiser spends above its daily budget by more than a small tolerance (1% or INR 1).
select spend_date, advertiser_id, gross_spend, daily_budget
from {{ ref('int_advertiser_daily_spend') }}
where gross_spend > daily_budget * 1.01 + 1
