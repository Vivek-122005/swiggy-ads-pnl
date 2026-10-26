"""Generalised second-price auction with reserve price and budget pacing.

Eligible campaigns (budget left, zone and category match, bid >= reserve) are ranked by
bid x predicted CTR. The winner of position k pays the minimum bid that would still have
kept it above the next-ranked bidder (score_{k+1} / pCTR_k), never below the reserve and
never above its own bid. No eligible bid means an unfilled slot.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class AuctionResult:
    winners: np.ndarray          # indices into the candidate arrays, length <= n_positions
    prices: np.ndarray           # CPC (or CPM for banners) paid by each winner
    reserve_bound: np.ndarray    # bool: price was set by the reserve
    n_bidders: int               # eligible bidders that entered this auction


def gsp(bids: np.ndarray, pctr: np.ndarray, reserve: float, n_positions: int,
        rng: np.random.Generator, score_noise_sd: float = 0.18) -> AuctionResult:
    ok = bids >= reserve
    idx = np.flatnonzero(ok)
    if idx.size == 0:
        return AuctionResult(np.empty(0, int), np.empty(0), np.empty(0, bool), 0)
    q = pctr[idx] * rng.lognormal(0.0, score_noise_sd, idx.size)   # platform's noisy quality estimate
    score = bids[idx] * q
    order = np.argsort(-score, kind="stable")
    k = min(n_positions, idx.size)
    top = order[:k]
    nxt_score = np.append(score[order[1:k + 1]], np.zeros(max(0, k + 1 - idx.size)))[:k]
    raw_price = nxt_score / q[top]
    prices = np.minimum(bids[idx][top], np.maximum(reserve, raw_price))
    reserve_bound = raw_price <= reserve
    prices = np.maximum(np.floor(prices * 100 + 1e-9) / 100, reserve)   # paise, never above bid
    return AuctionResult(idx[top], prices, reserve_bound, int(idx.size))


def pacing_throttle(spent_today: np.ndarray, daily_budget: np.ndarray, share_of_day_elapsed: float) -> np.ndarray:
    """Probability each campaign enters an auction this hour (even-delivery pacing).

    A campaign ahead of its even-spend line is throttled; one that has hit its budget stops.
    """
    target = daily_budget * min(1.0, share_of_day_elapsed + 0.08)
    ahead = spent_today / np.maximum(target, 1e-9)
    p = np.clip(1.6 - ahead, 0.0, 1.0)
    p[spent_today >= daily_budget] = 0.0
    return p
