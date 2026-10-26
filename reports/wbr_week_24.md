# WBR — Week 24 (5–11 Oct 2026)

*Simulated data. Not Swiggy data. Source: `marts.kpi_weekly`, data checks in [`analysis/wbr_week_24.ipynb`](../analysis/wbr_week_24.ipynb); dbt test `warn_click_log_gap`.*

**Headline:** CTR dropped to **1.34% on Wed 7 Oct** (from about 1.46%). This is **a data problem, not a business problem**: the click log lost 9.7% of click events that day, while billing, revenue and orders were normal. Weekly ad revenue was flat at ₹25.20 L (+0.2% WoW).

### Scorecard

| Metric | This week | Last week | WoW | vs 4-wk avg |
|---|---|---|---|---|
| Ad revenue (gross) | ₹25.20 L | ₹25.16 L | +0.2% | +0.1% |
| CPM (eCPM) | ₹224 | ₹223 | +0.4% | +0.2% |
| CTR | 1.50% | 1.53% | −0.02 pp | −0.02 pp |
| Fill rate | 92.4% | 92.4% | +0.0 pp | −0.4 pp |
| Active advertisers | 1,296 | 1,299 | −0.2% | +1.5% |
| ROAS | 4.71x | 4.68x | +0.5% | +1.7% |

### What drove it — business or data?

| Wed 7 Oct vs neighbouring days | Mon–Tue | **Wed 7** | Thu |
|---|---|---|---|
| Logged CTR | 1.44–1.47% | **1.34%** | 1.49% |
| Billed CTR (billing system) | 1.44–1.47% | **1.48%** | 1.49% |
| Billed vs logged clicks gap | 0.0% | **9.7%** (21,760 vs 19,645) | 0.0% |
| Platform orders per 1,000 impressions | 38.0–38.1 | **38.0** | 38.3 |

- **Two independent systems disagree on one day only.** Billing (the money) counted a normal CTR; the click event log is short by 2,115 clicks.
- **Demand did not move.** Orders per impression were steady, so users behaved normally. When orders per impression stay flat while CTR falls, the cause is the data.
- **The revenue bridge shows the same artefact:** CTR −₹0.30 L offset by "price" +₹0.45 L. The missing clicks shrink the CTR term and inflate implied CPC by the same amount, while billed revenue is unchanged.
- The dbt warning test `warn_click_log_gap` flagged the day automatically. It is the only day in 26 weeks with a material gap.

### Impact
- **No revenue impact**: revenue comes from billing.
- **Attribution is understated for that day.** Clicks missing from the log cannot claim their orders: 2,217 attributed orders against about 2,420 on Mon–Tue (about −8%). That understates ROAS in advertiser reports for 7 Oct.

### Recommendation
| Action | Owner | By |
|---|---|---|
| Backfill the 7 Oct click events from the ad-server log, then rerun attribution and refresh advertiser ROAS reports | Data engineering | Wed 14 Oct |
| Promote the billed-vs-logged click check from a warning to a paging alert (gap > 3% on any day) | Analytics engineering | Fri 16 Oct |

**Do not** act on the CTR dip: no rollbacks, no pricing changes.

### Watch list
Daily billed vs logged clicks gap · attributed orders for 7 Oct after the backfill · new advertisers (45 this week, up from 33) as pre-festive onboarding begins.
