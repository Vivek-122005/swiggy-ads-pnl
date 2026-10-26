select campaign_id, advertiser_id, surface, billing_type, target_zones, start_date, end_date,
       initial_daily_budget, initial_bid, category
from {{ ref('stg_campaigns') }}
