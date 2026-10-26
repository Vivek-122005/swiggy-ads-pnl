{#-
  THE METRIC DICTIONARY IN CODE. Every metric has exactly one definition here.
  kpi_weekly computes every value from these entries; the dashboard only reads kpi_weekly /
  rpt_* tables and never computes a metric of its own.

  num / den  : additive components summed over the period BEFORE dividing (never average daily ratios)
  scale      : multiplier applied after dividing (e.g. 1000 for per-mille)
  unit       : inr | pct | ratio | count | x
  good       : up | down | neutral  (colour of a change on the dashboard)
  jd         : one of the 6 KPIs named in the Swiggy BA (Ads) JD
  level      : cell = available for any product/zone/segment slice; account = advertiser-level, 'all' slices only
-#}
{% macro metric_catalogue() %}
  {{ return([
    {'metric': 'ad_revenue', 'label': 'Ad revenue (gross)', 'num': 'gross_revenue', 'den': none, 'scale': 1, 'unit': 'inr', 'good': 'up', 'jd': true, 'level': 'cell',
     'definition': 'Money billed to advertisers in the period: CPC charges + banner impressions / 1,000 x CPM. Gross of credits.'},
    {'metric': 'ecpm', 'label': 'CPM (eCPM)', 'num': 'gross_revenue', 'den': 'impressions', 'scale': 1000, 'unit': 'inr', 'good': 'up', 'jd': true, 'level': 'cell',
     'definition': 'Revenue earned per 1,000 ad impressions across all billing types = ad revenue / impressions x 1,000.'},
    {'metric': 'ctr', 'label': 'CTR', 'num': 'clicks', 'den': 'impressions', 'scale': 1, 'unit': 'pct', 'good': 'up', 'jd': true, 'level': 'cell',
     'definition': 'Share of ad impressions that got a valid click = clicks / impressions (summed first, then divided).'},
    {'metric': 'fill_rate', 'label': 'Fill rate', 'num': 'filled_requests', 'den': 'ad_requests', 'scale': 1, 'unit': 'pct', 'good': 'up', 'jd': true, 'level': 'inventory',
     'definition': 'Share of ad slots that showed a paid ad = filled ad requests / total ad requests.'},
    {'metric': 'active_advertisers', 'label': 'Active advertisers', 'num': 'active_advertisers', 'den': none, 'scale': 1, 'unit': 'count', 'good': 'up', 'jd': true, 'level': 'cell',
     'definition': 'Distinct advertisers with gross spend > 0 in the WEEK (weekly count is not the sum of daily counts).'},
    {'metric': 'roas', 'label': 'ROAS', 'num': 'attributed_gmv', 'den': 'gross_revenue', 'scale': 1, 'unit': 'x', 'good': 'up', 'jd': true, 'level': 'cell',
     'definition': 'Attributed GMV per rupee of ad spend. Attribution = last click by the same user on the same advertiser within 24h, booked on click date. Overstates true lift (cannibalised organic orders).'},
    {'metric': 'net_ad_revenue', 'label': 'Ad revenue (net)', 'num': 'net_revenue', 'den': none, 'scale': 1, 'unit': 'inr', 'good': 'up', 'jd': false, 'level': 'cell',
     'definition': 'Gross ad revenue less credits (disputes, make-goods, invalid-traffic credits), restated to the original billing date.'},
    {'metric': 'ad_requests', 'label': 'Ad requests', 'num': 'ad_requests', 'den': none, 'scale': 1, 'unit': 'count', 'good': 'up', 'jd': false, 'level': 'inventory',
     'definition': 'Ad slot opportunities created by sessions that opened the feed, search or home screen (one per slot position).'},
    {'metric': 'impressions', 'label': 'Impressions', 'num': 'impressions', 'den': none, 'scale': 1, 'unit': 'count', 'good': 'up', 'jd': false, 'level': 'cell',
     'definition': 'Paid ads actually shown (all served impressions are treated as viewable in this simulation).'},
    {'metric': 'clicks', 'label': 'Clicks', 'num': 'clicks', 'den': none, 'scale': 1, 'unit': 'count', 'good': 'up', 'jd': false, 'level': 'cell',
     'definition': 'Valid logged clicks: repeat clicks by the same user on the same campaign within 30 seconds count once.'},
    {'metric': 'cpc', 'label': 'CPC', 'num': 'cpc_revenue', 'den': 'cpc_clicks', 'scale': 1, 'unit': 'inr', 'good': 'neutral', 'jd': false, 'level': 'cell',
     'definition': 'Average price per click on CPC products = CPC revenue / valid clicks on CPC products. Falls when competition per auction falls.'},
    {'metric': 'cvr', 'label': 'Conversion rate', 'num': 'attributed_orders', 'den': 'clicks', 'scale': 1, 'unit': 'pct', 'good': 'up', 'jd': false, 'level': 'cell',
     'definition': 'Share of valid clicks that led to an attributed order = attributed orders / clicks.'},
    {'metric': 'attributed_orders', 'label': 'Attributed orders', 'num': 'attributed_orders', 'den': none, 'scale': 1, 'unit': 'count', 'good': 'up', 'jd': false, 'level': 'cell',
     'definition': 'Orders credited to an ad click under the 24h last-click rule.'},
    {'metric': 'attributed_gmv', 'label': 'Attributed GMV', 'num': 'attributed_gmv', 'den': none, 'scale': 1, 'unit': 'inr', 'good': 'up', 'jd': false, 'level': 'cell',
     'definition': 'Order value of attributed orders.'},
    {'metric': 'bid_density', 'label': 'Bid density', 'num': 'bidders_sum', 'den': 'ad_requests', 'scale': 1, 'unit': 'ratio', 'good': 'up', 'jd': false, 'level': 'inventory',
     'definition': 'Average number of eligible bidders per auction = sum of bidders / auctions. Leading indicator of CPC and fill.'},
    {'metric': 'reserve_binding_rate', 'label': 'Reserve-binding rate', 'num': 'reserve_binding_count', 'den': 'filled_requests', 'scale': 1, 'unit': 'pct', 'good': 'down', 'jd': false, 'level': 'inventory',
     'definition': 'Share of filled auctions where the reserve price set the price. High = thin competition; the reserve is doing the work.'},
    {'metric': 'budget_utilisation', 'label': 'Budget utilisation', 'num': 'account_gross_spend', 'den': 'account_budget', 'scale': 1, 'unit': 'pct', 'good': 'up', 'jd': false, 'level': 'account',
     'definition': 'Share of planned budget actually spent = spend / sum of daily budgets of active campaigns. Low = under-delivery.'},
    {'metric': 'new_advertisers', 'label': 'New advertisers', 'num': 'new_advertisers', 'den': none, 'scale': 1, 'unit': 'count', 'good': 'up', 'jd': false, 'level': 'account',
     'definition': 'Advertisers whose first-ever spend falls in the week.'},
    {'metric': 'churned_advertisers', 'label': 'Churned advertisers', 'num': 'churned_advertisers', 'den': none, 'scale': 1, 'unit': 'count', 'good': 'down', 'jd': false, 'level': 'account',
     'definition': 'Advertisers active the previous week and inactive for 4 straight weeks from this week. Confirmed 4 weeks later; the last 3 weeks are provisional (null).'},
    {'metric': 'arpa', 'label': 'Revenue per advertiser (ARPA)', 'num': 'gross_revenue', 'den': 'active_advertisers', 'scale': 1, 'unit': 'inr', 'good': 'up', 'jd': false, 'level': 'cell',
     'definition': 'Average spend per active advertiser = ad revenue / active advertisers. Skewed by a few big chains; read with the median.'},
    {'metric': 'median_spend', 'label': 'Median spend per advertiser', 'num': 'median_spend', 'den': none, 'scale': 1, 'unit': 'inr', 'good': 'up', 'jd': false, 'level': 'cell',
     'definition': 'Median weekly spend across active advertisers (4-week comparison = average of weekly medians).'},
    {'metric': 'top10_concentration', 'label': 'Top-10 concentration', 'num': 'top10_revenue', 'den': 'gross_revenue', 'scale': 1, 'unit': 'pct', 'good': 'down', 'jd': false, 'level': 'cell',
     'definition': 'Share of revenue from the 10 largest advertisers of the week. Risk metric: one big account pausing moves the P&L.'},
    {'metric': 'ad_take_rate', 'label': 'Ad take rate', 'num': 'gross_revenue_with_gov', 'den': 'gov', 'scale': 1, 'unit': 'pct', 'good': 'up', 'jd': false, 'level': 'gov',
     'definition': 'Ad revenue as a share of gross order value (all platform orders, ads + organic). Banners count against Instamart GOV.'},
    {'metric': 'click_log_gap', 'label': 'Billed vs logged click gap', 'num': 'click_gap', 'den': 'billed_clicks', 'scale': 1, 'unit': 'pct', 'good': 'down', 'jd': false, 'level': 'cell',
     'definition': 'DATA-QUALITY metric: (billed CPC clicks - valid logged CPC clicks) / billed CPC clicks. Near zero normally; a jump means a tracking problem, not a business change.'}
  ]) }}
{% endmacro %}
