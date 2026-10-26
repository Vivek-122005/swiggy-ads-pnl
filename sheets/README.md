# Google Sheets variance model + Data Studio

*All data is simulated. Not Swiggy data.*

```
GitHub Actions (every Monday) ──► dbt marts ──► dashboard/site/data/*.csv on Pages
                                                     │  IMPORTDATA (auto-refresh)
                                                     ▼
                                    Google Sheet "Ads P&L — weekly variance analysis"
                                      ├─ Variance  (formulas: scorecard, revenue bridge,
                                      │             product & zone variance, CTR mix vs rate)
                                      ├─ Pivot     (zone × week revenue)
                                      └─ grey data tabs (kpi_weekly, kpi_cube, …)
                                                     │  Google Sheets connector
                                                     ▼
                                    Data Studio report (5 pages, shareable link)
```

## Build the Sheet

1. Create a blank Google Sheet and copy its id from the URL.
2. Go to [script.google.com](https://script.google.com) → New project. Paste [`build_variance_workbook.gs`](build_variance_workbook.gs) and set `SPREADSHEET_ID`.
3. Run `buildAdsPnlWorkbook` and approve access to Sheets and external URLs (needed for `IMPORTDATA`).

The Variance tab only has formulas: pick a week (2–26) and a product in `B4:B5`, and every section recomputes from the live data tabs. Each section ends with a check row: the bridge effects must add up to the revenue change, and the mix and rate effects must add up to the actual CTR change.

## Why Sheets and not BigQuery for Data Studio

The data is pre-aggregated (a few thousand rows), so a Sheet is a free, zero-maintenance source that refreshes with the pipeline. The dbt project still has a `bigquery` target; use [`scripts/load_bigquery.py`](../scripts/load_bigquery.py) if you want Data Studio on BigQuery instead.
