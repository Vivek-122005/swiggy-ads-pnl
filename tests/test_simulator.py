"""Unit tests for simulator logic (auction, behaviour, pacing, calendar, determinism)."""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from simulator.auction import gsp, pacing_throttle
from simulator.behaviour import cvr, fatigue, order_delays_seconds, true_ctr
from simulator.traffic import Calendar

CFG_PATH = Path(__file__).resolve().parents[1] / "config" / "sim_config.yaml"


@pytest.fixture(scope="module")
def cfg():
    with open(CFG_PATH) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------- auction
def test_gsp_ranks_by_bid_times_ctr_and_pays_second_price():
    rng = np.random.default_rng(0)
    bids = np.array([10.0, 20.0, 15.0])
    pctr = np.array([0.05, 0.01, 0.04])          # scores: 0.5, 0.2, 0.6
    r = gsp(bids, pctr, reserve=1.0, n_positions=2, rng=rng, score_noise_sd=0.0)
    assert list(r.winners) == [2, 0]
    # winner pays next score / own pCTR: 0.5 / 0.04 = 12.5, never above own bid
    assert r.prices[0] == pytest.approx(12.5)
    assert r.prices[1] == pytest.approx(0.2 / 0.05)
    assert r.n_bidders == 3


def test_gsp_price_never_below_reserve_or_above_bid():
    rng = np.random.default_rng(1)
    for _ in range(200):
        n = rng.integers(1, 30)
        bids = rng.uniform(1, 30, n)
        pctr = rng.uniform(0.005, 0.06, n)
        r = gsp(bids, pctr, reserve=6.0, n_positions=5, rng=rng)
        assert np.all(r.prices >= 6.0 - 1e-9)
        assert np.all(r.prices <= bids[r.winners] + 1e-9)


def test_gsp_bids_below_reserve_leave_slot_unfilled():
    r = gsp(np.array([2.0, 3.0]), np.array([0.05, 0.05]), reserve=6.0, n_positions=3,
            rng=np.random.default_rng(0))
    assert r.winners.size == 0 and r.n_bidders == 0


def test_last_bidder_pays_reserve_and_is_flagged():
    r = gsp(np.array([20.0]), np.array([0.03]), reserve=6.0, n_positions=1,
            rng=np.random.default_rng(0), score_noise_sd=0.0)
    assert r.prices[0] == 6.0 and bool(r.reserve_bound[0])


# ---------------------------------------------------------------- pacing
def test_pacing_stops_at_budget_and_throttles_when_ahead():
    budget = np.array([100.0, 100.0, 100.0])
    spent = np.array([100.0, 80.0, 10.0])
    p = pacing_throttle(spent, budget, share_of_day_elapsed=0.3)
    assert p[0] == 0.0          # exhausted
    assert p[1] < p[2]          # ahead of even pace -> throttled harder
    assert p[2] == 1.0


# ---------------------------------------------------------------- behaviour
def test_ctr_decays_with_position(cfg):
    sc = cfg["surfaces"]["food_listing"]
    ctrs = [true_ctr(sc["base_ctr"], d, 1.0, np.array([1.0]), np.array([1.0]))[0] for d in sc["pos_decay"]]
    assert all(a > b for a, b in zip(ctrs, ctrs[1:]))


def test_fatigue_falls_with_exposure():
    f = fatigue(np.array([0, 1_000, 100_000]), 0.1)
    assert f[0] == 1.0 and f[0] > f[1] > f[2] > 0


def test_low_rating_drags_cvr(cfg):
    lo = cvr(cfg, "food_listing", np.array([3.0]), np.array([500.0]))[0]
    hi = cvr(cfg, "food_listing", np.array([4.5]), np.array([500.0]))[0]
    assert hi > lo


def test_order_delay_tail_share(cfg):
    d = order_delays_seconds(np.random.default_rng(3), 50_000, 22, 0.07)
    late = (d > 24 * 3600).mean()
    assert 0.06 < late < 0.08
    assert np.median(d) < 3600


# ---------------------------------------------------------------- calendar / anomalies
def test_weeks_run_monday_to_sunday(cfg):
    cal = Calendar(copy.deepcopy(cfg), np.random.default_rng(0))
    assert cal.dates[0].dayofweek == 0
    assert cal.dates[-1].dayofweek == 6
    assert len(cal.dates) == cfg["calendar"]["weeks"] * 7


def test_planted_anomaly_windows(cfg):
    cal = Calendar(copy.deepcopy(cfg), np.random.default_rng(0))
    start = pd.Timestamp(cfg["calendar"]["start_date"])
    wk = lambda w, d=0: start + pd.Timedelta(weeks=w - 1, days=d)
    assert cal.in_anomaly("A1", wk(6)) and not cal.in_anomaly("A1", wk(8))
    assert cal.in_anomaly("A3", wk(12)) and cal.in_anomaly("A3", wk(26, 6))
    assert cal.in_anomaly("A6", wk(24, 2)) and not cal.in_anomaly("A6", wk(24, 3))
    assert sum(cal.in_anomaly("A4", wk(15, d)) for d in range(7)) == 3


def test_rain_shock_raises_sessions_only_on_rain_days(cfg):
    cal = Calendar(copy.deepcopy(cfg), np.random.default_rng(0))
    start = pd.Timestamp(cfg["calendar"]["start_date"])
    tue_15 = start + pd.Timedelta(weeks=14, days=1)
    tue_16 = start + pd.Timedelta(weeks=15, days=1)
    assert cal.day_factor(tue_15, "food") > cal.day_factor(tue_16, "food") * 1.2


# ---------------------------------------------------------------- determinism
@pytest.mark.slow
def test_same_seed_same_numbers(cfg, tmp_path):
    from simulator.run import Simulator
    outs = []
    for i in range(2):
        sim = Simulator(copy.deepcopy(cfg), external_dir=tmp_path / "none", weeks=1)
        sim.run(verbose=False)
        sim.write(tmp_path / f"r{i}", tmp_path / f"k{i}")
        outs.append(pd.read_csv(tmp_path / f"r{i}" / "raw_billing.csv.gz"))
    pd.testing.assert_frame_equal(outs[0], outs[1])
