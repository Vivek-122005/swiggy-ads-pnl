-- GRAIN: week x product x metric (product = 'all' or one surface).
-- Every value is computed from metric_catalogue(): components are summed over the period first,
-- then divided. four_week_avg is computed from the SUMMED components of the 4 prior weeks
-- (a true 4-week ratio, not an average of weekly ratios).
{% set metrics = metric_catalogue() %}
{% set comps = [] %}
{% for m in metrics %}
  {% for c in [m.num, m.den] %}{% if c and c not in comps %}{% do comps.append(c) %}{% endif %}{% endfor %}
{% endfor %}
{% set account_comps = ['account_gross_spend', 'account_budget', 'new_advertisers', 'churned_advertisers'] %}

with cube as (
    select * from {{ ref('rpt_kpi_cube_weekly') }}
    where zone_id = 'all' and advertiser_segment = 'all'
),
account as (
    select week_start,
           sum(gross_spend)                                      as account_gross_spend,
           sum(case when is_active then budget else 0 end)       as account_budget,
           sum(case when is_new then 1 else 0 end)               as new_advertisers,
           sum(case when is_churned then 1 else 0 end)           as churned_advertisers_raw,
           count(*) - count(is_churned)                          as churn_pending
    from {{ ref('fct_advertiser_weekly') }}
    group by 1
),
base as (
    select
        cube.week_start, cube.week_number, cube.surface as product,
        {% for c in comps if c not in account_comps %}
        cast(cube.{{ c }} as {{ float_type() }}) as {{ c }},
        {% endfor %}
        cast(case when cube.surface = 'all' then a.account_gross_spend end as {{ float_type() }}) as account_gross_spend,
        cast(case when cube.surface = 'all' then a.account_budget end as {{ float_type() }})      as account_budget,
        -- week 1 is left-censored (every existing advertiser looks "new"), so new advertisers start at week 2
        cast(case when cube.surface = 'all' and cube.week_number > 1 then a.new_advertisers end as {{ float_type() }}) as new_advertisers,
        cast(case when cube.surface = 'all' and a.churn_pending = 0 then a.churned_advertisers_raw end as {{ float_type() }}) as churned_advertisers
    from cube
    left join account a on a.week_start = cube.week_start
),
windowed as (
    select
        *,
        {% for c in comps %}
        lag({{ c }}) over (partition by product order by week_start) as prev_{{ c }},
        sum({{ c }}) over (partition by product order by week_start rows between 4 preceding and 1 preceding) as p4_{{ c }},
        count({{ c }}) over (partition by product order by week_start rows between 4 preceding and 1 preceding) as n4_{{ c }},
        {% endfor %}
        1 as _
    from base
),
long as (
    {% for m in metrics %}
    select
        week_start, week_number, product,
        '{{ m.metric }}' as metric,
        {{ loop.index }} as metric_order,
        {% if m.den %}
        {{ safe_divide(m.num, m.den) }} * {{ m.scale }}                         as value,
        {{ safe_divide('prev_' ~ m.num, 'prev_' ~ m.den) }} * {{ m.scale }}     as prior_week_value,
        {{ safe_divide('p4_' ~ m.num, 'p4_' ~ m.den) }} * {{ m.scale }}         as four_week_avg
        {% else %}
        {{ m.num }} * {{ m.scale }}                                             as value,
        prev_{{ m.num }} * {{ m.scale }}                                        as prior_week_value,
        {{ safe_divide('p4_' ~ m.num, 'n4_' ~ m.num) }} * {{ m.scale }}         as four_week_avg
        {% endif %}
    from windowed
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
),
catalogue as (
    {% for m in metrics %}
    select '{{ m.metric }}' as metric, '{{ m.label }}' as metric_label, '{{ m.unit }}' as unit,
           '{{ m.good }}' as good_direction, {{ 'true' if m.jd else 'false' }} as is_jd_metric,
           '{{ m.level }}' as metric_level, '{{ m.definition | replace("'", "''") }}' as definition
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
)
select
    {{ dbt_utils.generate_surrogate_key(['l.week_start', 'l.product', 'l.metric']) }} as kpi_key,
    l.week_start, l.week_number, l.product, l.metric, l.metric_order,
    c.metric_label, c.unit, c.good_direction, c.is_jd_metric, c.definition,
    l.value, l.prior_week_value,
    {{ safe_divide('l.value - l.prior_week_value', 'abs(l.prior_week_value)') }} as wow_pct,
    l.four_week_avg,
    {{ safe_divide('l.value - l.four_week_avg', 'abs(l.four_week_avg)') }}       as vs_4wk_pct
from long l
join catalogue c using (metric)
where l.value is not null
