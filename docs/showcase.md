# Showcase kit

*Everything here describes a simulated marketplace. Say so whenever you share it.*

## Resume bullets

- Built an end-to-end **ads P&L reporting system** for a simulated Bengaluru food + quick-commerce ads marketplace. It covers **~290 M impressions, 4.4 M clicks and 2,300 advertisers over 26 weeks**, using Python, dbt and DuckDB (BigQuery-ready), with automated weekly refreshes on GitHub Actions.
- Defined **24 ads KPIs** (revenue, eCPM, CTR, fill rate, ROAS, bid density, reserve-binding rate, budget utilisation, churn…) in a single dbt metric catalogue, guarded by **91 automated data-quality tests**: reconciliation to billing, no-overspend, completeness, and grain uniqueness.
- Shipped a **5-page live dashboard** and a **Google Sheets variance model**. Both include a revenue bridge that splits each weekly change into requests, fill rate, CTR and CPC, and the bridge reconciles to the rupee.
- Diagnosed **7 planted KPI anomalies** and wrote one-page WBRs. One example: an 8% CTR drop traced to a single Android ad slot (₹1.35 L/week). Another: a reserve-price change that raised banner CPM 10% but cut banner revenue 18%. A third: a one-day CTR dip proven to be a logging gap, not a business change.

## 2-minute interview story

1. **Why.** Ads is a high-margin growth line for food and quick-commerce apps, so I built the weekly reporting an ads team runs every Monday.
2. **What.** It's a seeded simulator of second-price auctions across 15 Bengaluru zones and 3 ad products, feeding a dbt warehouse with one tested metric layer, a live dashboard and a Sheets variance model.
3. **Best finding (week 12).** Leadership raised the banner reserve price 20% expecting flat revenue. Banner CPM rose 10%, but fill fell from 84% to 64% because 17 of 37 banner campaigns now bid under the floor. Revenue fell 17.6%, about ₹6 L over the half. I recommended reverting, or A/B-testing ₹150 by zone.
4. **Rigor.** I planted the anomalies with an answer key that no model reads, so I can show my analysis found the real causes. In week 24 it also told a *data* problem apart from a *business* problem: billed and logged clicks disagreed on one day while orders per impression held steady.
5. **Next.** An A/B-test module (CUPED, guardrails) using the same simulator, where I know the true effect.

## LinkedIn post (draft)

> I built the weekly ads P&L reporting an ads team would run, for a *simulated* Bengaluru food + quick-commerce marketplace: auction simulator → dbt warehouse (24 KPIs, 91 tests) → live dashboard → one-page business reviews.
>
> Favourite finding: a 20% reserve-price increase raised banner CPM 10% but cut banner revenue 18%, because 17 of 37 campaigns were priced out of the auction. Higher price ≠ higher revenue when fill collapses.
>
> Dashboard: http://vivekbuilds.me/swiggy-ads-pnl/ · Code: github.com/Vivek-122005/swiggy-ads-pnl
> (All data simulated; restaurant/brand names from public Kaggle datasets.)

## Links

| What | Where |
|---|---|
| Live dashboard | http://vivekbuilds.me/swiggy-ads-pnl/ |
| Metric dictionary + lineage (dbt docs) | http://vivekbuilds.me/swiggy-ads-pnl/docs/ |
| Executed WBR notebooks | http://vivekbuilds.me/swiggy-ads-pnl/analysis/ |
| WBR memos | [`reports/`](../reports/) |
