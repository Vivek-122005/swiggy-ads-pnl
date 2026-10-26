# WBR — Week 12 (13–19 Jul 2026)

*Simulated data. Not Swiggy data. Source: `marts.rpt_inventory_weekly`, `marts.rpt_revenue_bridge`, `marts.kpi_weekly`; investigation: [`analysis/wbr_week_12.ipynb`](../analysis/wbr_week_12.ipynb).*

**Headline:** The 20% banner reserve-price increase (₹140 → ₹168 CPM) raised banner CPM 10% but **cut banner fill from 84% to 64%, so banner revenue fell 17.6% WoW (₹2.42 L → ₹1.99 L)** and total ad revenue fell 2.0% to ₹23.87 L.

### Scorecard

| Metric | This week | Last week | WoW | vs 4-wk avg |
|---|---|---|---|---|
| Ad revenue (gross) | ₹23.87 L | ₹24.36 L | −2.0% | −0.3% |
| CPM (eCPM) | ₹224 | ₹223 | +0.4% | +1.7% |
| CTR | 1.52% | 1.49% | +0.03 pp | +0.02 pp |
| Fill rate | 90.8% | 94.2% | −3.5 pp | −3.7 pp |
| Active advertisers | 1,266 | 1,285 | −1.5% | −1.5% |
| ROAS | 4.23x | 4.09x | +3.5% | +5.6% |

### What drove it

1. **Data and demand checked:** billed and logged clicks match, and requests are up 1.3%. The fill drop is real and comes from the supply side.
2. **Bridge (−₹0.49 L):** fill **−₹0.72 L**, of which **banners −₹0.58 L**. Banner price partly offset it at **+₹0.17 L**, and requests added +₹0.39 L.
3. **Auction health on home banners, week 11 → 12:**

   | | Wk 11 | Wk 12 |
   |---|---|---|
   | Fill rate | 84.2% | 63.8% |
   | Reserve-binding rate | 35.0% | 56.9% |
   | Bid density | 1.84 | 1.03 |
   | Avg clearing CPM | ₹160 | ₹176 |

4. **Who got priced out:** 17 of 37 live banner campaigns now bid below the ₹168 reserve, up from 8 below the old ₹140. Those campaigns stopped clearing, leaving about 3.67 L banner requests unfilled.
5. Plan expected "CPM up, fill down, revenue roughly flat". **In fact the fill loss outweighs the price gain about 3:1.**

### Impact
- **−₹0.43 L of banner revenue per week**, which weeks 13–16 confirm (₹1.84–1.99 L/week). That is about **−₹6 L over the rest of the half** if nothing changes.
- The extra unfilled inventory was worth about ₹0.59 L/week at last week's eCPM.

### Recommendation
| Action | Owner | By |
|---|---|---|
| Revert the banner reserve to ₹140, or A/B test ₹150 vs ₹168 across zones before changing it citywide | Ads pricing / product | Fri 24 Jul |
| Give bid guidance to the 9 banner advertisers newly priced out (bids between ₹140 and ₹168) | Brand sales | Wed 22 Jul |

### Watch list
Banner fill and reserve-binding rate · banner revenue vs the ₹2.4 L/week baseline · count of banner campaigns bidding below the reserve.
