-- The four bridge effects must add up to the revenue change (identity holds exactly).
select week_number, surface, revenue_change, residual
from {{ ref('rpt_revenue_bridge') }}
where abs(residual) > 1.0
