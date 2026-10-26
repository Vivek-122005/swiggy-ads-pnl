-- One calendar: IST dates, weeks Monday-Sunday, week 1 = the week of var('start_date').
with spine as (
    {{ dbt_utils.date_spine(datepart="day",
                            start_date="cast('" ~ var('start_date') ~ "' as date)",
                            end_date=dbt.dateadd('day', 1, "cast('" ~ var('end_date') ~ "' as date)")) }}
)
select
    cast(date_day as date)                                                        as date_day,
    {{ week_start('date_day') }}                                                  as week_start,
    cast(floor({{ dbt.datediff("cast('" ~ var('start_date') ~ "' as date)", 'cast(date_day as date)', 'day') }} / 7) as {{ dbt.type_int() }}) + 1 as week_number,
    cast({{ dbt.date_trunc('month', 'date_day') }} as date)                       as month_start,
    case when {{ dbt.datediff(week_start('date_day'), 'cast(date_day as date)', 'day') }} >= 5 then true else false end as is_weekend,
    {{ dbt.datediff(week_start('date_day'), 'cast(date_day as date)', 'day') }} + 1 as day_of_week   -- 1 = Monday
from spine
