-- Every date in the window is present in every daily feed (no missing partitions).
{% set feeds = [('stg_ad_requests', 'event_date'), ('stg_impressions', 'event_date'), ('stg_clicks', 'click_date'),
                ('stg_billing', 'billing_date'), ('stg_platform_daily', 'order_date'), ('stg_campaign_budget_daily', 'budget_date')] %}
{% for model, col in feeds %}
select '{{ model }}' as feed, d.date_day
from {{ ref('dim_date') }} d
left join (select distinct {{ col }} as dt from {{ ref(model) }}) f on f.dt = d.date_day
where f.dt is null
{% if not loop.last %}union all{% endif %}
{% endfor %}
