{{ config(severity = 'warn') }}
-- A week-over-week move above the threshold on a JD metric raises a WARNING (worth a look), not a failure.
select week_number, metric, value, prior_week_value, wow_pct
from {{ ref('kpi_weekly') }}
where product = 'all' and is_jd_metric and abs(wow_pct) > {{ var('wow_warn_threshold') }}
