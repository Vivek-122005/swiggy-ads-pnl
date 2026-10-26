# WBR — Week 24 (5–11 Oct 2026)

*Simulated data. Not Swiggy data. Source: `marts.kpi_weekly`, data checks in [`analysis/wbr_week_24.ipynb`](../analysis/wbr_week_24.ipynb); dbt test `warn_click_log_gap`.*

**Headline:** CTR dropped to **1.36% on Wed 7 Oct** (from about 1.52%). This is **a data problem, not a business problem**: the click log lost 10.1% of click events that day, while billing, revenue and orders were normal. Weekly ad revenue was ₹24.65 L (−1.0% WoW).

### Scorecard

| Metric | This week | Last week | WoW | vs 4-wk avg |
|---|---|---|---|---|
| Ad revenue (gross) | ₹24.65 L | ₹24.89 L | −1.0% | −1.0% |
| CPM (eCPM) | ₹225 | ₹222 | +1.4% | +0.4% |
| CTR | 1.55% | 1.55% | −0.00 pp | −0.01 pp |
| Fill rate | 90.3% | 91.5% | −1.2 pp | −1.2 pp |
| Active advertisers | 1,271 | 1,256 | +1.2% | +1.7% |
| ROAS | 4.61x | 4.79x | −3.7% | −1.2% |

### What drove it — business or data?

| Wed 7 Oct vs neighbouring days | Mon–Tue | **Wed 7** | Thu |
|---|---|---|---|
| Logged CTR | 1.47–1.52% | **1.36%** | 1.54% |
| Billed CTR (billing system) | 1.47–1.52% | **1.52%** | 1.54% |
| Billed vs logged clicks gap | 0.0% | **10.1%** (21,742 vs 19,546) | 0.0% |
| Platform orders per 1,000 impressions | 38.8–39.0 | **38.9** | 38.9 |

- **Two independent systems disagree on one day only.** Billing (the money) counted a normal CTR; the click event log is short by 2,196 clicks.
- **Demand did not move.** Orders per impression were steady, so users behaved normally. When orders per impression stay flat while CTR falls, the cause is the data.
- The dbt warning test `warn_click_log_gap` flagged the day automatically. This is the only day in 26 weeks with a non-zero gap.

### Impact
- **No revenue impact**: revenue comes from billing.
- **Attribution is understated for that day.** Clicks missing from the log cannot claim their orders: 2,168 attributed orders against about 2,350 on the days around it (about −8%). That understates ROAS in advertiser reports for 7 Oct.
- The weekly fill dip (−1.2 pp) is separate from this incident and sits in **home banners** (66.2% → 60.1%, about −₹0.19 L in the bridge): two banner contracts ended and fewer bids clear the higher reserve set in week 12. Food and Instamart fill moved less than 0.6 pp.

### Recommendation
| Action | Owner | By |
|---|---|---|
| Backfill the 7 Oct click events from the ad-server log, then rerun attribution and refresh advertiser ROAS reports | Data engineering | Wed 14 Oct |
| Promote the billed-vs-logged click check from a warning to a paging alert (gap > 3% on any day) | Analytics engineering | Fri 16 Oct |

**Do not** act on the CTR dip: no rollbacks, no pricing changes.

### Watch list
Daily billed vs logged clicks gap · attributed orders for 7 Oct after the backfill · new advertisers (49 this week, up from 21) as pre-festive onboarding begins.
