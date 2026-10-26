-- Advertiser x day: what they spent vs what their live campaigns were allowed to spend.
with budget as (
    select b.budget_date as spend_date, c.advertiser_id,
           sum(case when b.campaign_status = 'active' then b.daily_budget else 0 end) as daily_budget,
           max(case when b.campaign_status = 'active' then 1 else 0 end)               as has_active_campaign
    from {{ ref('stg_campaign_budget_daily') }} b
    join {{ ref('stg_campaigns') }} c using (campaign_id)
    group by 1, 2
),
spend as (
    select billing_date as spend_date, advertiser_id,
           sum(gross_amount) as gross_spend, sum(net_amount) as net_spend
    from {{ ref('int_billing_net') }}
    group by 1, 2
)
select
    coalesce(b.spend_date, s.spend_date)          as spend_date,
    coalesce(b.advertiser_id, s.advertiser_id)    as advertiser_id,
    coalesce(s.gross_spend, 0)                    as gross_spend,
    coalesce(s.net_spend, 0)                      as net_spend,
    coalesce(b.daily_budget, 0)                   as daily_budget,
    coalesce(b.has_active_campaign, 0) = 1        as has_active_campaign
from budget b
full outer join spend s
  on b.spend_date = s.spend_date and b.advertiser_id = s.advertiser_id
