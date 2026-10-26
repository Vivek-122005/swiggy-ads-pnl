-- Revenue bridge, week over week, from the revenue identity:
--   CPC products:  revenue = ad requests x fill rate x CTR x CPC
--   CPM banners:   revenue = ad requests x fill rate x (revenue per impression)   [= eCPM / 1,000]
-- Sequential substitution in the fixed order requests -> fill -> CTR -> price, so the four
-- effects add up EXACTLY to the change in revenue (impressions = filled requests by construction;
-- here CTR uses valid logged clicks and CPC = revenue / those clicks, so the identity is exact).
with p as (
    select week_start, week_number, surface,
           cast(ad_requests as {{ float_type() }}) as q,
           {{ safe_divide('filled_requests', 'ad_requests') }} as f,
           case when surface = 'home_banner' then 1.0 else {{ safe_divide('clicks', 'impressions') }} end as c,
           case when surface = 'home_banner' then {{ safe_divide('gross_revenue', 'impressions') }}
                else {{ safe_divide('gross_revenue', 'clicks') }} end as p,
           gross_revenue as revenue
    from {{ ref('rpt_kpi_cube_weekly') }}
    where zone_id = 'all' and advertiser_segment = 'all' and surface <> 'all'
),
pairs as (
    select cur.week_start, cur.week_number, cur.surface,
           prv.revenue as revenue_prior, cur.revenue as revenue_current,
           prv.q as q0, prv.f as f0, prv.c as c0, prv.p as p0,
           cur.q as q1, cur.f as f1, cur.c as c1, cur.p as p1
    from p cur
    join p prv on prv.surface = cur.surface and prv.week_number = cur.week_number - 1
),
effects as (
    select week_start, week_number, surface, revenue_prior, revenue_current,
           (q1 - q0) * f0 * c0 * p0                         as requests_effect,
           q1 * (f1 - f0) * c0 * p0                         as fill_effect,
           q1 * f1 * (c1 - c0) * p0                         as ctr_effect,
           q1 * f1 * c1 * (p1 - p0)                         as price_effect,
           q0, q1, f0, f1, c0, c1, p0, p1
    from pairs
)
select
    {{ dbt_utils.generate_surrogate_key(['week_start', 'surface']) }} as bridge_key,
    week_start, week_number, surface, revenue_prior, revenue_current,
    revenue_current - revenue_prior as revenue_change,
    requests_effect, fill_effect, ctr_effect, price_effect,
    (revenue_current - revenue_prior) - (requests_effect + fill_effect + ctr_effect + price_effect) as residual,
    q0 as requests_prior, q1 as requests_current, f0 as fill_prior, f1 as fill_current,
    case when surface = 'home_banner' then null else c0 end as ctr_prior,
    case when surface = 'home_banner' then null else c1 end as ctr_current,
    case when surface = 'home_banner' then p0 * 1000 else p0 end as price_prior,      -- CPC, or eCPM for banners
    case when surface = 'home_banner' then p1 * 1000 else p1 end as price_current
from effects
union all
select
    {{ dbt_utils.generate_surrogate_key(['week_start', "'all'"]) }}, week_start, week_number, 'all',
    sum(revenue_prior), sum(revenue_current), sum(revenue_current - revenue_prior),
    sum(requests_effect), sum(fill_effect), sum(ctr_effect), sum(price_effect),
    sum((revenue_current - revenue_prior) - (requests_effect + fill_effect + ctr_effect + price_effect)),
    sum(q0), sum(q1), null, null, null, null, null, null
from effects
group by week_start, week_number
