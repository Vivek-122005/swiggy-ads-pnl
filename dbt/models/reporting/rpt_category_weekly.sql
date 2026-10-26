-- Categories (cuisines for restaurants, Instamart categories for brands): spend, CTR, ROAS, growth.
with base as (
    select d.week_start, d.week_number, a.advertiser_type, a.category,
           sum(f.gross_revenue) as gross_revenue, sum(f.impressions) as impressions, sum(f.clicks) as clicks,
           sum(f.attributed_orders) as attributed_orders, sum(f.attributed_gmv) as attributed_gmv,
           count(distinct case when f.gross_revenue > 0 then f.advertiser_id end) as active_advertisers
    from {{ ref('fct_ads_daily') }} f
    join {{ ref('dim_date') }} d on d.date_day = f.event_date
    join {{ ref('dim_advertiser') }} a using (advertiser_id)
    group by 1, 2, 3, 4
)
select
    {{ dbt_utils.generate_surrogate_key(['week_start', 'advertiser_type', 'category']) }} as category_week_key,
    *,
    {{ safe_divide('clicks', 'impressions') }}             as ctr,
    {{ safe_divide('attributed_orders', 'clicks') }}       as cvr,
    {{ safe_divide('attributed_gmv', 'gross_revenue') }}   as roas,
    {{ safe_divide('gross_revenue - avg(gross_revenue) over (partition by advertiser_type, category order by week_number rows between 4 preceding and 1 preceding)',
                   'avg(gross_revenue) over (partition by advertiser_type, category order by week_number rows between 4 preceding and 1 preceding)') }} as spend_vs_4wk_pct
from base
