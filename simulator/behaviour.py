"""User behaviour: CTR, conversion, order value, order timing, ad fatigue."""
from __future__ import annotations

import numpy as np

PEAK_HOURS = {12, 13, 14, 19, 20, 21, 22}
LATE_HOURS = {0, 1, 2, 3, 4, 5}


def hour_ctr_factor(cfg: dict, hour: int) -> float:
    b = cfg["behaviour"]
    if hour in PEAK_HOURS:
        return b["hour_ctr_factor_peak"]
    if hour in LATE_HOURS:
        return b["hour_ctr_factor_late"]
    return 1.0


def fatigue(prev_day_impressions: np.ndarray, strength: float) -> np.ndarray:
    """CTR multiplier that falls as a campaign's recent exposure grows."""
    return 1.0 / (1.0 + strength * np.log1p(prev_day_impressions / 500.0))


def true_ctr(base_ctr: float, pos_decay: float, hour_f: float, quality: np.ndarray,
             fatigue_f: np.ndarray, extra: float = 1.0) -> np.ndarray:
    return np.clip(base_ctr * pos_decay * hour_f * quality * fatigue_f * extra, 0.0, 0.5)


def cvr(cfg: dict, surface: str, rating: np.ndarray, price: np.ndarray) -> np.ndarray:
    b = cfg["behaviour"]
    base = {"food_listing": b["food_cvr_base"], "instamart_search": b["instamart_cvr_base"],
            "home_banner": b["banner_cvr_base"]}[surface]
    rating_f = np.exp(0.9 * (rating - 4.0))               # low-rated restaurants drag CVR down
    price_f = np.clip((600.0 / np.maximum(price, 100.0)) ** 0.25, 0.7, 1.3)  # premium -> lower CVR
    return np.clip(base * rating_f * price_f, 0.005, 0.6)


def order_values(rng: np.random.Generator, surface: str, ref_price: np.ndarray) -> np.ndarray:
    if surface == "food_listing":
        v = rng.lognormal(np.log(np.maximum(ref_price, 150) * 0.78), 0.32)
    else:
        v = rng.lognormal(np.log(np.maximum(ref_price, 120) * 1.15), 0.40)
    return np.round(np.clip(v, 79, 9999), 0)


def order_delays_seconds(rng: np.random.Generator, n: int, median_min: float, late_share: float) -> np.ndarray:
    """Click-to-order delay. Most orders follow within minutes; a tail arrives after 24h."""
    d = rng.lognormal(np.log(median_min * 60), 0.9, n)
    d = np.minimum(d, 23.5 * 3600)
    late = rng.random(n) < late_share
    d[late] = rng.uniform(24.2 * 3600, 72 * 3600, late.sum())
    return d.astype(np.int64)
