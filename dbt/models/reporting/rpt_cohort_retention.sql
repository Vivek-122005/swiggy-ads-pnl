-- Weekly cohort retention: of advertisers whose first spend was in week C, the share active k weeks later.
with a as (
    select first_active_week as cohort_week, week_number, week_number - first_active_week as weeks_since_first,
           advertiser_id, is_active
    from {{ ref('fct_advertiser_weekly') }}
),
size as (
    select cohort_week, count(distinct advertiser_id) as cohort_size from a group by 1
)
select
    {{ dbt_utils.generate_surrogate_key(['a.cohort_week', 'a.weeks_since_first']) }} as cohort_key,
    a.cohort_week, a.weeks_since_first, s.cohort_size,
    sum(case when a.is_active then 1 else 0 end) as active_advertisers,
    {{ safe_divide('sum(case when a.is_active then 1 else 0 end)', 's.cohort_size') }} as retention
from a join size s using (cohort_week)
group by a.cohort_week, a.weeks_since_first, s.cohort_size
