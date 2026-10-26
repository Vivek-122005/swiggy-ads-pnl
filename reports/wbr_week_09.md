# WBR — Week 9 (22–28 Jun 2026)

*Simulated data. Not Swiggy data. Source: `marts.kpi_weekly`, `marts.fct_advertiser_weekly`, `marts.rpt_inventory_weekly`; investigation: [`analysis/wbr_week_09.ipynb`](../analysis/wbr_week_09.ipynb).*

**Headline:** Ad revenue fell **2.0% WoW to ₹23.68 L** because **NUTRIWISH, our largest Instamart advertiser (₹1.08 L/week, 4.4% of revenue), paused every campaign**. Instamart revenue fell 5.3% and top-10 concentration dropped from 16.9% to 14.0%.

### Scorecard

| Metric | This week | Last week | WoW | vs 4-wk avg |
|---|---|---|---|---|
| Ad revenue (gross) | ₹23.68 L | ₹24.16 L | −2.0% | −2.2% |
| CPM (eCPM) | ₹220 | ₹221 | −0.3% | +0.2% |
| CTR | 1.52% | 1.47% | +0.05 pp | +0.09 pp |
| Fill rate | 94.3% | 95.5% | −1.2 pp | −1.5 pp |
| Active advertisers | 1,283 | 1,296 | −1.0% | −1.1% |
| ROAS | 4.03x | 3.69x | +9.3% | +14.0% |

### What drove it

1. **Data check passed:** billed and logged clicks match on every day.
2. **Bridge (−₹0.48 L):** price −₹0.80 L, fill −₹0.37 L, CTR **+₹0.73 L**, requests −₹0.04 L. Instamart accounts for −₹0.39 L of the change.
3. **One account explains it.** The advertiser page shows NUTRIWISH (snacks, with a portfolio across Instamart categories) going from ₹1.08 L to ₹0 of spend, with budget utilisation at zero. No other advertiser lost more than ₹0.33 L.
4. **The marketplace absorbed about 63% of the gap.** Other brands won the freed slots, so Instamart revenue fell only ₹0.39 L against a ₹1.08 L pause. With less competition, CPC fell 3% (₹13.97 → ₹13.55). The replacement ads had higher CTR, which is why CTR and ROAS *rose* (NUTRIWISH's own ROAS was 3.3x, below average).
5. **Fill dropped where it was often the only strong bidder.** In the thin categories, fill fell from 85.8% to 71.7% in frozen and from 83.6% to 69.2% in baby care, where bid density is just 2.4. Snacks stayed full, but its clearing price fell from ₹20.5 to ₹19.4.

### Impact
- **−₹0.48 L total revenue (−₹0.39 L Instamart) per week while the pause lasts**: about ₹2 L over a month.
- It is a concentration risk, not a performance problem. One account carried 4.4% of revenue, and frozen and baby-care inventory depends on it.

### Recommendation
| Action | Owner | By |
|---|---|---|
| Call NUTRIWISH to learn why they paused (budget cycle, ROAS vs target, competitor) and offer a ROAS review of their 3.3x | Instamart brand sales lead | Tue 30 Jun |
| Recruit 5+ brands in frozen and baby care, where fill depends on 2–3 bidders | Category sales (Instamart) | 31 Jul |

### Watch list
NUTRIWISH spend · fill rate in frozen, baby care and staples · Instamart CPC · top-10 concentration.

> **Postscript (week 11):** NUTRIWISH returned at ₹1.20 L/week; Instamart revenue recovered to ₹7.43 L.
