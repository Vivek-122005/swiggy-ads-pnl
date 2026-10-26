with first_spend as (
    select advertiser_id, min(spend_date) as first_spend_date
    from {{ ref('int_advertiser_daily_spend') }}
    where gross_spend > 0
    group by 1
)
select
    a.advertiser_id, a.advertiser_name, a.advertiser_type, a.advertiser_segment, a.is_chain,
    a.category, a.home_zone_id, a.rating, a.price_reference, a.joined_on, a.name_source,
    f.first_spend_date,
    d.week_number                                   as first_active_week
from {{ ref('stg_advertisers') }} a
left join first_spend f using (advertiser_id)
left join {{ ref('dim_date') }} d on d.date_day = f.first_spend_date
