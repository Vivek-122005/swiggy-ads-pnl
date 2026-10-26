# WBR — Week 9 (22–28 Jun 2026)

*Simulated data. Not Swiggy data. Source: `marts.kpi_weekly`, `marts.fct_advertiser_weekly`, `marts.rpt_inventory_weekly`; investigation: [`analysis/wbr_week_09.ipynb`](../analysis/wbr_week_09.ipynb).*

**Headline:** Ad revenue fell **2.1% WoW to ₹23.53 L** because **NUTRIWISH, our largest Instamart advertiser (₹1.18 L/week, 4.9% of revenue), paused every campaign**. Instamart revenue fell 6.8% and top-10 concentration dropped from 16.7% to 14.0%.

### Scorecard

| Metric | This week | Last week | WoW | vs 4-wk avg |
|---|---|---|---|---|
| Ad revenue (gross) | ₹23.53 L | ₹24.03 L | −2.1% | −2.8% |
| CPM (eCPM) | ₹218 | ₹220 | −1.0% | −0.7% |
| CTR | 1.50% | 1.47% | +0.03 pp | +0.08 pp |
| Fill rate | 94.9% | 95.7% | −0.8 pp | −1.3 pp |
| Active advertisers | 1,274 | 1,297 | −1.8% | −1.1% |
| ROAS | 4.08x | 3.69x | +10.5% | +13.3% |

### What drove it

1. **Data check passed:** billed and logged clicks match on every day.
2. **Bridge (−₹0.50 L):** price −₹0.75 L, fill −₹0.28 L, CTR **+₹0.55 L**, requests −₹0.01 L. Instamart accounts for essentially all of it (−₹0.50 L); food listings were flat.
3. **One account explains it.** The advertiser page shows NUTRIWISH (snacks, with a portfolio across Instamart categories) going from ₹1.18 L to ₹0 of spend, with budget utilisation at zero. No other advertiser lost more than ₹0.11 L.
4. **The marketplace absorbed about 58% of the gap.** Other brands won the freed slots, so Instamart revenue fell ₹0.50 L against a ₹1.18 L pause. With less competition, CPC fell 3.1% (₹13.89 → ₹13.46). The replacement ads had higher CTR, which is why CTR and ROAS *rose* (NUTRIWISH's own ROAS was 3.4x, below average).
5. **Fill dropped where it was often the only strong bidder.** In the thin categories, fill fell from 85.7% to 70.4% in frozen and from 86.0% to 71.4% in baby care, where bid density fell from about 3.3 to 2.4. Snacks stayed full (99.7%), but its clearing price fell from ₹19.8 to ₹18.4.

### Impact
- **−₹0.50 L of Instamart revenue per week while the pause lasts**: about ₹2 L over a month.
- It is a concentration risk, not a performance problem. One account carried about 5% of revenue, and frozen and baby-care inventory depends on it.

### Recommendation
| Action | Owner | By |
|---|---|---|
| Call NUTRIWISH to learn why they paused (budget cycle, ROAS vs target, competitor) and offer a ROAS review of their 3.4x | Instamart brand sales lead | Tue 30 Jun |
| Recruit 5+ brands in frozen and baby care, where fill depends on 2–3 bidders | Category sales (Instamart) | 31 Jul |

### Watch list
NUTRIWISH spend · fill rate in frozen, baby care and staples · Instamart CPC · top-10 concentration.

> **Postscript (week 11):** NUTRIWISH returned at ₹1.29 L/week; Instamart revenue recovered to ₹7.23 L.
