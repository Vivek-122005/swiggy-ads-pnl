# WBR — Week 12 (13–19 Jul 2026)

*Simulated data. Not Swiggy data. Source: `marts.rpt_inventory_weekly`, `marts.rpt_revenue_bridge`, `marts.kpi_weekly`; investigation: [`analysis/wbr_week_12.ipynb`](../analysis/wbr_week_12.ipynb).*

**Headline:** The 20% banner reserve-price increase (₹140 → ₹168 CPM) raised banner CPM 8% but **cut banner fill from 91% to 77%, so banner revenue fell 9.1% WoW (₹2.66 L → ₹2.42 L)**. Total ad revenue slipped 0.7% to ₹24.15 L.

### Scorecard

| Metric | This week | Last week | WoW | vs 4-wk avg |
|---|---|---|---|---|
| Ad revenue (gross) | ₹24.15 L | ₹24.33 L | −0.7% | +1.4% |
| CPM (eCPM) | ₹223 | ₹221 | +0.6% | +1.8% |
| CTR | 1.50% | 1.49% | +0.00 pp | +0.00 pp |
| Fill rate | 92.8% | 95.0% | −2.2 pp | −2.2 pp |
| Active advertisers | 1,289 | 1,293 | −0.3% | +0.4% |
| ROAS | 4.14x | 4.12x | +0.4% | +2.6% |

### What drove it

1. **Data and demand checked:** billed and logged clicks match, and requests are up 1.0%. The fill drop is real and comes from the supply side.
2. **Bridge (−₹0.17 L):** fill **−₹0.40 L**, almost all of it from **banners (−₹0.42 L)**. Banner price partly offset it at **+₹0.18 L**. Food growth (+₹0.21 L) masks the banner loss in the headline number.
3. **Auction health on home banners, week 11 → 12:**

   | | Wk 11 | Wk 12 |
   |---|---|---|
   | Fill rate | 91.1% | 76.6% |
   | Reserve-binding rate | 24.6% | 51.8% |
   | Bid density | 2.35 | 1.45 |
   | Avg clearing CPM | ₹164 | ₹177 |

4. **Who got priced out:** 19 of 42 live banner campaigns now bid below the ₹168 reserve, up from 8 below the old ₹140. Those 11 campaigns stopped clearing, and unfilled banner requests rose from 1.61 L to 4.22 L.
5. Plan expected "CPM up, fill down, revenue roughly flat". **In fact the fill loss outweighs the price gain about 2.4:1.**

### Impact
- **About −₹0.25 L of banner revenue per week**, confirmed in weeks 12–17 (₹2.32–2.42 L/week vs ₹2.57–2.66 L before). That is about **−₹3.5 L over the rest of the half** if nothing changes.
- The extra 2.6 L unfilled requests were worth about ₹0.43 L/week at last week's eCPM.

### Recommendation
| Action | Owner | By |
|---|---|---|
| Revert the banner reserve to ₹140, or A/B test ₹150 vs ₹168 across zones before changing it citywide | Ads pricing / product | Fri 24 Jul |
| Give bid guidance to the 11 banner advertisers newly priced out (bids between ₹140 and ₹168) | Brand sales | Wed 22 Jul |

### Watch list
Banner fill and reserve-binding rate · banner revenue vs the ₹2.6 L/week baseline · count of banner campaigns bidding below the reserve.
