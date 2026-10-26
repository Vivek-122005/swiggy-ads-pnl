# Dashboard (hosted on GitHub Pages)

A static, five-page dashboard for the weekly ads P&L review. **All data is simulated, not Swiggy data.**

| Page | Question it answers |
|---|---|
| Summary | How did ads do last week? 6 JD scorecards (value, vs last week, vs 4-week average), 26-week revenue trend, revenue by product, 3 biggest movers |
| Revenue drivers | Why did revenue change? Waterfall bridge (requests → fill → CTR → price), driver trends, CTR by position × platform |
| Inventory & auction | Are we selling our slots well? Zone × hour fill heatmap, bid density, reserve-binding rate, clearing-price distribution, unfilled premium slots |
| Advertisers | Who is growing, who is leaving? Active / new / churned, cohort retention, top-10 concentration, ROAS by category, top accounts with budget use |
| Zones & categories | Where should sales focus? Zone bubble map (revenue, ROAS), category table, "grow or fix" quadrant |

Controls on every page: week, product, zone, advertiser type. State lives in the URL hash
(`#/drivers?w=6&p=food_listing`), so any view can be linked.

## How it is built

```
dbt marts ──► dashboard/export.py ──► site/data/*.json ──► site/ (index.html + app.js + styles.css)
```

* `site/` is plain HTML/CSS/JS, no build step. Charts use ECharts 5.5.1 from jsDelivr.
* `export.py` runs read-only SQL against the DuckDB warehouse and writes one JSON file per
  query in its `EXPORTS` dict, plus `meta.json` (refresh time, data note, links).
* GitHub Actions runs `make all` (simulate → dbt build/test → export) and deploys `site/` to Pages.
  The JSON is generated in CI and is **not committed** (`site/data/*.json` is gitignored).

### Metric discipline

The browser never defines a metric. With no zone/advertiser-type filter, scorecards read
`kpi_weekly` directly. With a filter, they read the matching pre-aggregated row of
`rpt_kpi_cube_weekly` (every product × zone × advertiser-type combination, including `all`
roll-ups, so distinct counts stay exact) and apply the **same formula** as
`dbt/macros/metric_catalogue.sql`: sum numerator and denominator first, then divide.
Inventory metrics (requests, fill, bid density, reserve binding) have no advertiser dimension,
so the dashboard says so instead of guessing. Any chart a control can't filter shows a
"Not filterable by …" note.

## JSON contract

Each file is `{"columns": [...], "rows": [[...], ...]}`. Files and columns are defined in one
place: the `EXPORTS` dict in `export.py`.

| File | Grain | Source mart |
|---|---|---|
| `kpi_weekly` | week × product × metric | `kpi_weekly` |
| `metrics` | metric (label, unit, good direction, definition) | `kpi_weekly` |
| `kpi_cube` | week × product × zone × advertiser segment (+ `all`) | `rpt_kpi_cube_weekly` |
| `revenue_bridge` | week × product | `rpt_revenue_bridge` |
| `movers` | week × rank (top 3) | `rpt_biggest_movers` |
| `zones` | week × zone | `rpt_zone_weekly` |
| `categories` | week × advertiser type × category | `rpt_category_weekly` |
| `cohorts` | first-spend week × weeks since | `rpt_cohort_retention` |
| `fill_heatmap` | week × zone × hour | `rpt_inventory_weekly` |
| `inventory_surface` | week × surface × request category | `rpt_inventory_weekly` |
| `unfilled_premium` | week × zone × surface × peak hour | `rpt_inventory_weekly` |
| `clearing_price_dist` | week × surface × ₹ bucket | `fct_inventory_hourly` |
| `platform_weekly` | week × surface × position × platform | `fct_ads_platform_daily` |
| `top_advertisers` | week × advertiser (top 25 + last week's top 25) | `rpt_top_advertisers_weekly` |
| `advertiser_weekly_summary` | week | `fct_advertiser_weekly` |
| `zones_dim`, `weeks` | dimensions | `dim_zone`, `dim_date` |

## Run it locally

```bash
make all                                    # builds data/warehouse.duckdb and site/data/*.json
python -m http.server -d dashboard/site 8000
```

`mock_data.py` is a **dev fixture only**: it rebuilds the same JSON files with pandas straight from
`data/raw` so the UI can be worked on without a warehouse. Its numbers approximate the marts and
must never be published.
