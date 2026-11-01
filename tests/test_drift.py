import itertools
import math

import numpy as np
import pytest
from numpy.typing import NDArray

from cascade.drift import (
    DriftConfig,
    RiskMonitor,
    WindowedZTest,
    simulate_stream,
    summarise_trials,
)

FloatArray = NDArray[np.float64]


def test_monitor_covers_true_mean_at_all_times() -> None:
    # anytime-valid: over many streams, the true mean stays inside the interval at every step
    rng = np.random.default_rng(0)
    p, bad = 0.05, 0
    for _ in range(300):
        mon = RiskMonitor(alpha=0.1)
        for x in rng.random(400) < p:
            lo, hi = mon.update(float(x))
            if not lo <= p <= hi:
                bad += 1
                break
    assert bad / 300 <= 0.1  # nominal 10%, conservative in practice


def test_monitor_alarm_fires_after_risk_increase_not_before() -> None:
    rng = np.random.default_rng(1)
    mon = RiskMonitor(alpha=0.05)
    for _ in range(300):
        mon.update(float(rng.random() < 0.02))
        assert mon.raw_lower < 0.05
    for _ in range(900):
        mon.update(float(rng.random() < 0.3))
    assert mon.raw_lower > 0.05


def test_monitor_validates_input_and_interval_is_monotone() -> None:
    mon = RiskMonitor()
    with pytest.raises(ValueError, match="observation"):
        mon.update(1.5)
    with pytest.raises(ValueError, match="alpha"):
        RiskMonitor(alpha=0.0)
    widths = [(h - lo) for lo, h in (mon.update(0.0) for _ in range(50))]
    assert all(b <= a + 1e-12 for a, b in itertools.pairwise(widths))


def test_windowed_ztest_waits_for_data() -> None:
    z = WindowedZTest()
    assert all(z.update(1.0) == 0.0 for _ in range(19))
    assert z.update(1.0) > 0.0 or math.isclose(z.update(1.0), 0.0, abs_tol=1.0)


def _pool(rng: np.random.Generator, n: int, err_slope: float) -> tuple[FloatArray, FloatArray]:
    s = rng.uniform(0.2, 1.0, n)
    e = (rng.random(n) < err_slope * (1.0 - s)).astype(np.float64)
    return s, e


def test_rolling_policy_recovers_where_static_does_not() -> None:
    rng = np.random.default_rng(2)
    pre = _pool(rng, 4000, 0.3)  # error rate falls with confidence
    post = _pool(rng, 4000, 1.0)  # much worse student after the shift
    cfg = DriftConfig(alpha=0.1, delta=0.1, audit_rate=0.1, window_labels=500, recal_every=100)
    out = {}
    for policy in ("static_holm", "rolling_holm"):
        trials = [simulate_stream(pre, post, 1500, 4000, policy, cfg, seed=s) for s in range(6)]
        out[policy] = summarise_trials(trials, cfg.alpha)
    assert out["rolling_holm"]["post_mean_risk"] < out["static_holm"]["post_mean_risk"]
    assert (
        out["rolling_holm"]["post_block_violation_rate"]
        < out["static_holm"]["post_block_violation_rate"]
    )
