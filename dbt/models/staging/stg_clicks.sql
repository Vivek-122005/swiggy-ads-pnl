-- Valid clicks: a repeat click by the same user on the same campaign within
-- var('duplicate_click_seconds') of their previous click counts once (double taps).
with typed as (
    select
        cast(click_id as {{ dbt.type_string() }})    as click_id,
        {{ to_ts('click_ts') }}                       as click_ts,
        cast(user_id as {{ dbt.type_bigint() }})      as user_id,
        cast(campaign_id as {{ dbt.type_string() }})  as campaign_id,
        cast(zone_id as {{ dbt.type_string() }})      as zone_id,
        cast(surface as {{ dbt.type_string() }})      as surface,
        cast(position as {{ dbt.type_int() }})        as slot_position,
        cast(platform as {{ dbt.type_string() }})     as platform
    from {{ source('raw', 'raw_clicks') }}
),

sequenced as (
    select
        *,
        lag(click_ts) over (partition by user_id, campaign_id order by click_ts, click_id) as prev_click_ts
    from typed
)

select
    click_id, click_ts, cast(click_ts as date) as click_date, user_id, campaign_id,
    zone_id, surface, slot_position, platform
from sequenced
where prev_click_ts is null
   or {{ dbt.datediff('prev_click_ts', 'click_ts', 'second') }} > {{ var('duplicate_click_seconds') }}
