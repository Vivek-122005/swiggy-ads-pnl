# WBR — Week 21 (14–20 Sep 2026)

*Simulated data. Not Swiggy data. Source: `marts.rpt_zone_weekly`, `intermediate.int_clicks_enriched`, `marts.kpi_weekly`; investigation: [`analysis/wbr_week_21.ipynb`](../analysis/wbr_week_21.ipynb).*

**Headline:** Ad revenue rose **1.7% WoW to ₹25.54 L**, but **₹0.54 L of it is billed invalid traffic**: a click bot in **Whitefield** made 4,131 clicks from 40 user IDs with zero orders. Whitefield clicks rose 32% while its conversion fell from 11.1% to 8.4%. Without the bot, revenue was about flat (−0.5%).

### Scorecard

| Metric | This week | Last week | WoW | vs 4-wk avg |
|---|---|---|---|---|
| Ad revenue (gross) | ₹25.54 L | ₹25.12 L | +1.7% | +2.4% |
| CPM (eCPM) | ₹226 | ₹222 | +1.5% | +1.4% |
| CTR | 1.55% | 1.51% | +0.04 pp | +0.04 pp |
| Fill rate | 92.5% | 94.0% | −1.4 pp | −1.2 pp |
| Active advertisers | 1,271 | 1,260 | +0.9% | +0.5% |
| ROAS | 4.58x | 4.56x | +0.5% | +2.5% |

### What drove it

1. **Data check passed:** billed equals logged clicks, so the clicks really happened and were really billed.
2. **Bridge (+₹0.42 L):** CTR **+₹0.50 L**, requests +₹0.40 L (Ganesh Chaturthi Monday lifted every zone), fill −₹0.31 L (home banners), price −₹0.17 L.
3. **CTR up while CVR falls is the fraud signature.** Drilling down by zone, **91% of the click increase sits in Whitefield** (14,198 → 18,678 clicks; CTR 1.53% → 1.91%), while its CVR fell from 11.1% to 8.4% and its orders were flat (1,574 → 1,573). Every other zone's CTR stayed in its normal 1.45–1.57% band.
4. **User-level check:** 40 user IDs in Whitefield made **4,131 clicks (about 100 each) and placed 0 orders**. No genuine user made more than 3 ad clicks in the week. The pattern stops in week 22 (14,592 clicks).

### Impact
- About **₹0.54 L billed to advertisers for invalid clicks** (4,131 × ₹13.10 CPC). Underlying revenue was about flat (−0.5%), not +1.7%.
- Affected Whitefield advertisers saw ROAS diluted for the week. Left uncredited, that risks trust and churn among the chains concentrated there.

### Recommendation
| Action | Owner | By |
|---|---|---|
| Block the 40 IDs and add a frequency rule (>10 ad clicks/user/day → invalid) to the click filter | Trust & safety + ads engineering | Wed 23 Sep |
| Credit affected Whitefield advertisers about ₹0.54 L as an invalid-traffic adjustment (it lands in net revenue) | Finance + ads sales | Fri 25 Sep |

### Watch list
Clicks per user per zone · CVR by zone (alert if CTR rises while CVR falls) · net vs gross revenue after credits.
