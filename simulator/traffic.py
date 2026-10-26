"""Sessions by zone, hour and platform for one simulated day.

sessions = base x zone weight x weekday factor x hour curve x seasonality x weather/event shocks x noise
"""
from __future__ import annotations

import numpy as np
import pandas as pd

VERTICALS = {"food": "food_sessions_per_day", "instamart": "instamart_sessions_per_day", "home": "home_sessions_per_day"}


class Calendar:
    """Day-level multipliers: seasonality (visible, normal) and planted shocks."""

    def __init__(self, cfg: dict, rng: np.random.Generator):
        self.cfg = cfg
        self.start = pd.Timestamp(cfg["calendar"]["start_date"])
        self.n_days = cfg["calendar"]["weeks"] * 7
        self.dates = pd.date_range(self.start, periods=self.n_days, freq="D")
        s = cfg["seasonality"]
        mw = pd.date_range(s["monsoon_window"][0], s["monsoon_window"][1], freq="D")
        # Random (normal) rain days during monsoon, excluding the planted heavy-rain week
        a4 = next(a for a in cfg["anomalies"] if a["id"] == "A4")
        a4_week_start = self.start + pd.Timedelta(weeks=a4["week"] - 1)
        cand = [d for d in mw if not (a4_week_start <= d < a4_week_start + pd.Timedelta(days=7))]
        self.rain_days = set(pd.to_datetime(rng.choice(np.array(cand, dtype="datetime64[ns]"), s["random_rain_days"], replace=False)))

    def week_of(self, d: pd.Timestamp) -> int:
        return int((d - self.start).days // 7) + 1

    def anomaly(self, aid: str) -> dict:
        return next(a for a in self.cfg["anomalies"] if a["id"] == aid)

    def in_anomaly(self, aid: str, d: pd.Timestamp) -> bool:
        a = self.anomaly(aid)
        wk = self.week_of(d)
        if "days" in a:  # specific weekdays (0=Mon) of the given week
            return wk == a["week"] and d.dayofweek in a["days"]
        if "day" in a:
            return wk == a["week"] and d.dayofweek == a["day"]
        return a["week"] <= wk < a["week"] + a.get("weeks_active", 1)

    def day_factor(self, d: pd.Timestamp, vertical: str) -> float:
        t = self.cfg["traffic"]
        s = self.cfg["seasonality"]
        f = t["weekday_factor"][d.dayofweek] * (1 + t["growth_per_week"]) ** (self.week_of(d) - 1)
        if d.normalize() in self.rain_days and vertical in ("food", "instamart"):
            f *= s["rain_session_boost"]
        if d == pd.Timestamp(s["ganesh_chaturthi"]):
            f *= s["ganesh_boost"]
        if self.in_anomaly("A4", d) and vertical in ("food", "instamart"):
            f *= self.anomaly("A4")["session_boost"]
        if self.in_anomaly("A7", d):
            f *= self.anomaly("A7")["session_boost"] * (1.08 if vertical == "instamart" else 1.0)
        return f

    def hour_factors(self, d: pd.Timestamp) -> np.ndarray:
        """Per-hour multiplier on top of the base curve (IPL nights, Friday night)."""
        s = self.cfg["seasonality"]
        h = np.ones(24)
        lo, hi = pd.Timestamp(s["ipl_match_window"][0]), pd.Timestamp(s["ipl_match_window"][1])
        if lo <= d <= hi:
            h[19:24] *= s["ipl_final_boost"] if d == pd.Timestamp(s["ipl_final"]) else s["ipl_evening_boost"]
        if d.dayofweek == 4:
            h[20:24] *= self.cfg["traffic"]["friday_night_boost"]
        return h


def day_sessions(cfg: dict, cal: Calendar, d: pd.Timestamp, zones: pd.DataFrame,
                 rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Return {vertical: int array [zone, hour, platform]} of sessions for date d."""
    t = cfg["traffic"]
    zw = zones["weight"].to_numpy()
    nz = len(zw)
    pmix = np.array([t["platform_mix"]["android"], t["platform_mix"]["ios"]])
    hf = cal.hour_factors(d)
    out = {}
    for v, key in VERTICALS.items():
        curve = np.asarray(t[f"{v}_hour_curve"], dtype=float)
        curve = curve / curve.sum()
        base = t[key] * cal.day_factor(d, v)
        zone_noise = rng.lognormal(0, t["noise_sd"], nz)
        hour_noise = rng.lognormal(0, t["noise_sd"] / 2, (nz, 24))
        lam = base * zw[:, None] * zone_noise[:, None] * curve[None, :] * hf[None, :] * hour_noise
        lam = lam[:, :, None] * pmix[None, None, :]
        out[v] = rng.poisson(lam)
    return out
