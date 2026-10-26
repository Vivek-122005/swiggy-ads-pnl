-- GRAIN: week x advertiser, for every week from the advertiser's first active week onward.
with weeks as (
    select distinct week_start, week_number from {{ ref('dim_date') }}
),
spend as (
    select d.week_start, s.advertiser_id,
           sum(s.gross_spend) as gross_spend, sum(s.net_spend) as net_spend,
           sum(s.daily_budget) as budget
    from {{ ref('int_advertiser_daily_spend') }} s
    join {{ ref('dim_date') }} d on d.date_day = s.spend_date
    group by 1, 2
),
perf as (
    select d.week_start, f.advertiser_id,
           sum(f.impressions) as impressions, sum(f.clicks) as clicks,
           sum(f.attributed_orders) as attributed_orders, sum(f.attributed_gmv) as attributed_gmv
    from {{ ref('fct_ads_daily') }} f
    join {{ ref('dim_date') }} d on d.date_day = f.event_date
    group by 1, 2
),
grid as (
    select w.week_start, w.week_number, a.advertiser_id, a.first_active_week
    from {{ ref('dim_advertiser') }} a
    join weeks w on w.week_number >= a.first_active_week
),
base as (
    select
        g.week_start, g.week_number, g.advertiser_id, g.first_active_week,
        coalesce(s.gross_spend, 0)        as gross_spend,
        coalesce(s.net_spend, 0)          as net_spend,
        coalesce(s.budget, 0)             as budget,
        coalesce(p.impressions, 0)        as impressions,
        coalesce(p.clicks, 0)             as clicks,
        coalesce(p.attributed_orders, 0)  as attributed_orders,
        coalesce(p.attributed_gmv, 0)     as attributed_gmv,
        case when coalesce(s.gross_spend, 0) > 0 then 1 else 0 end as active_flag
    from grid g
    left join spend s on s.week_start = g.week_start and s.advertiser_id = g.advertiser_id
    left join perf  p on p.week_start = g.week_start and p.advertiser_id = g.advertiser_id
),
windowed as (
    select
        *,
        lag(active_flag) over (partition by advertiser_id order by week_number) as prev_active_flag,
        sum(active_flag) over (partition by advertiser_id order by week_number
                               rows between current row and {{ var('churn_inactive_weeks') - 1 }} following) as active_next_n,
        count(*)         over (partition by advertiser_id order by week_number
                               rows between current row and {{ var('churn_inactive_weeks') - 1 }} following) as weeks_next_n
    from base
)
select
    {{ dbt_utils.generate_surrogate_key(['week_start', 'advertiser_id']) }} as advertiser_week_key,
    week_start, week_number, advertiser_id, first_active_week,
    gross_spend, net_spend, budget, impressions, clicks, attributed_orders, attributed_gmv,
    {{ safe_divide('attributed_gmv', 'gross_spend') }}  as roas,
    {{ safe_divide('gross_spend', 'budget') }}          as budget_utilisation,
    active_flag = 1                                      as is_active,
    week_number = first_active_week                      as is_new,
    -- churn: active last week, then inactive for N straight weeks starting now.
    -- null = not yet knowable (fewer than N weeks of future data).
    case
        when coalesce(prev_active_flag, 0) = 1 and active_flag = 0 and weeks_next_n < {{ var('churn_inactive_weeks') }} then null
        when coalesce(prev_active_flag, 0) = 1 and active_next_n = 0 then true
        else false
    end                                                  as is_churned
from windowed
