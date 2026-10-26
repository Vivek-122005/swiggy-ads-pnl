-- Attributed orders happen after their click and within the attribution window.
select order_id, minutes_click_to_order
from {{ ref('int_attributed_orders') }}
where minutes_click_to_order < 0 or minutes_click_to_order > {{ var('attribution_window_hours') }} * 60
