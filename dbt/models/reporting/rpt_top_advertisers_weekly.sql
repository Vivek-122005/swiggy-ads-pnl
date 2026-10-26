-- Top 25 advertisers by spend each week, with budget utilisation, ROAS and WoW change: the sales call list.
with w as (
    select f.*, a.advertiser_name, a.advertiser_segment, a.category,
           lag(f.gross_spend) over (partition by f.advertiser_id order by f.week_number) as prior_week_spend,
           row_number() over (partition by f.week_start order by f.gross_spend desc, f.advertiser_id) as spend_rank
    from {{ ref('fct_advertiser_weekly') }} f
    join {{ ref('dim_advertiser') }} a using (advertiser_id)
),
prev_top as (   -- keep last week's top 25 too, so a big account that paused still shows up at zero
    select week_number + 1 as week_number, advertiser_id from w where spend_rank <= 25
)
select
    {{ dbt_utils.generate_surrogate_key(['w.week_start', 'w.advertiser_id']) }} as top_adv_key,
    w.week_start, w.week_number, w.advertiser_id, w.advertiser_name, w.advertiser_segment, w.category,
    w.spend_rank, w.gross_spend, w.prior_week_spend,
    {{ safe_divide('w.gross_spend - w.prior_week_spend', 'w.prior_week_spend') }} as spend_wow_pct,
    w.budget, w.budget_utilisation, w.roas, w.is_active
from w
left join prev_top p on p.week_number = w.week_number and p.advertiser_id = w.advertiser_id
where w.spend_rank <= 25 or p.advertiser_id is not null
