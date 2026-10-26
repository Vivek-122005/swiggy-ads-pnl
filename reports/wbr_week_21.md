# WBR — Week 21 (14–20 Sep 2026)

*Simulated data. Not Swiggy data. Source: `marts.rpt_zone_weekly`, `intermediate.int_clicks_enriched`, `marts.kpi_weekly`; investigation: [`analysis/wbr_week_21.ipynb`](../analysis/wbr_week_21.ipynb).*

**Headline:** Ad revenue rose **3.9% WoW to ₹25.45 L**, but about **₹0.57 L of it is billed invalid traffic**. A click bot in **Whitefield** made 4,463 clicks from 40 user IDs with zero orders, lifting Whitefield clicks 42% while its conversion fell from 10.5% to 8.3%.

### Scorecard

| Metric | This week | Last week | WoW | vs 4-wk avg |
|---|---|---|---|---|
| Ad revenue (gross) | ₹25.45 L | ₹24.49 L | +3.9% | +4.2% |
| CPM (eCPM) | ₹227 | ₹225 | +1.3% | +1.4% |
| CTR | 1.59% | 1.54% | +0.04 pp | +0.04 pp |
| Fill rate | 91.5% | 91.5% | +0.0 pp | +0.2 pp |
| Active advertisers | 1,247 | 1,250 | −0.2% | −0.3% |
| ROAS | 4.56x | 4.50x | +1.3% | +0.8% |

### What drove it

1. **Data check passed:** billed equals logged clicks, so the clicks really happened and were really billed.
2. **Bridge (+₹0.97 L):** CTR **+₹0.72 L**, requests +₹0.63 L (Ganesh Chaturthi Monday lifted every zone), price −₹0.37 L.
3. **CTR up while CVR falls is the fraud signature.** Drilling down by zone, **63% of the click increase sits in Whitefield** (13,976 → 19,829 clicks; CTR 1.51% → 2.00%), while its CVR fell from 10.5% to 8.3%. Every other zone's CTR was flat.
4. **User-level check:** 40 user IDs in Whitefield made **4,463 clicks (about 110 each) and placed 0 orders**. No genuine user made more than 2 ad clicks in the week. The pattern stops in week 22 (14,553 clicks).

### Impact
- About **₹0.57 L billed to advertisers for invalid clicks** (4,463 × ₹12.8 CPC). Underlying revenue growth is +1.6%, not +3.9%.
- Affected Whitefield advertisers saw ROAS diluted for the week. Left uncredited, that risks trust and churn among the chains concentrated there.

### Recommendation
| Action | Owner | By |
|---|---|---|
| Block the 40 IDs and add a frequency rule (>10 ad clicks/user/day → invalid) to the click filter | Trust & safety + ads engineering | Wed 23 Sep |
| Credit affected Whitefield advertisers about ₹0.57 L as an invalid-traffic adjustment (it lands in net revenue) | Finance + ads sales | Fri 25 Sep |

### Watch list
Clicks per user per zone · CVR by zone (alert if CTR rises while CVR falls) · net vs gross revenue after credits.
