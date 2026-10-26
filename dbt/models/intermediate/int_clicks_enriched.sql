-- Valid clicks with the advertiser and billing type of the campaign that was clicked.
select
    k.click_id, k.click_ts, k.click_date, k.user_id, k.campaign_id, c.advertiser_id, c.billing_type,
    k.zone_id, k.surface, k.slot_position, k.platform
from {{ ref('stg_clicks') }} k
join {{ ref('stg_campaigns') }} c using (campaign_id)
