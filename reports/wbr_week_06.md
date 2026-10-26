# WBR — Week 6 (1–7 Jun 2026)

*Simulated data. Not Swiggy data. Source: `marts.kpi_weekly`, `marts.rpt_revenue_bridge`, `marts.fct_ads_platform_daily`; investigation: [`analysis/wbr_week_06.ipynb`](../analysis/wbr_week_06.ipynb).*

**Headline:** Ad revenue fell **7.6% WoW to ₹23.74 L**. About half is the expected post-IPL traffic drop; the other half is an **8.3% CTR fall on food listings that sits entirely in Android position 1** (2.35% → 1.37%). That pattern points to a product change, not to demand.

### Scorecard

| Metric | This week | Last week | WoW | vs 4-wk avg |
|---|---|---|---|---|
| Ad revenue (gross) | ₹23.74 L | ₹25.68 L | −7.6% | −6.9% |
| CPM (eCPM) | ₹217 | ₹225 | −3.3% | −4.0% |
| CTR | 1.37% | 1.45% | −0.08 pp | −0.07 pp |
| Fill rate | 96.4% | 96.6% | −0.2 pp | −0.4 pp |
| Active advertisers | 1,270 | 1,325 | −4.2% | −4.1% |
| ROAS | 3.63x | 3.58x | +1.4% | +4.9% |

### What drove it

1. **Data check passed.** Billed clicks equal logged clicks on all 7 days, and platform orders per 1,000 impressions held steady (36.3–37.1), so the CTR drop is not a logging gap.
2. **Revenue bridge (−₹1.94 L):** CTR **−₹1.17 L**, ad requests **−₹1.06 L**, fill −₹0.07 L, price **+₹0.37 L**.
3. **Requests fell 4.1%** because the IPL ended on 31 May (week 5 carried match-night evenings and the final). That is seasonality, not a problem.
4. **CTR is a rate effect, not a mix effect.** Of the −0.080 pp change, mix contributes +0.003 pp and rate −0.082 pp. Instamart (2.31% → 2.31%) and banners were flat; food listings fell 1.48% → 1.36%.
5. **It concentrates in one cell.** Android position 1 fell from 2.35% to 1.37% (−42%); iOS position 1 was flat (2.40% → 2.38%) and positions 2–5 on both platforms were flat. A change that hits one slot on one platform from one date onward matches an **Android app release that moved sponsored slot 1 below the fold**.

### Impact
- **10,203 lost clicks × ₹13.30 CPC ≈ ₹1.36 L of revenue this week**, and about ₹1.36 L every week until it is fixed.
- Advertisers in slot 1 lose ~42% of their Android clicks, so expect under-delivery complaints and budget pull-backs from chains bidding for the top slot. Active advertisers already fell 4.2%.

### Recommendation
| Action | Owner | By |
|---|---|---|
| Confirm the Android release that went out around 1 Jun and roll back or hotfix the slot-1 placement | Android app lead + Ads product | Wed 10 Jun |
| Proactively give make-good credits to the top 20 slot-1 advertisers for week 6 | Ads sales lead | Fri 12 Jun |

### Watch list (next week)
Android position-1 CTR, daily · food-listing CTR · budget utilisation for slot-1 advertisers · ad requests vs the post-IPL baseline.

> **Postscript (week 8):** after the fix, Android position-1 CTR recovered to 2.40% and food-listing CTR to 1.50%.
