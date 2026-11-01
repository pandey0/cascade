import numpy as np
from numpy.typing import NDArray
from scipy.stats import binom

from cascade.bounds import cp_upper
from cascade.gates import (
    certify_once,
    coarse_grid,
    default_grid,
    select_bonferroni,
    select_certified,
    select_holm,
    select_naive,
    select_safety_factor,
    select_split_sequence,
    select_wilson,
    wilson_upper,
)
from cascade.metrics import aurc, ece, risk_coverage


def _toy() -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    # 400 items at score 0.9 with 2 errors; 400 items at score 0.5 with 100 errors.
    scores = np.array([0.9] * 400 + [0.5] * 400)
    errors = np.array([1.0] * 2 + [0.0] * 398 + [1.0] * 100 + [0.0] * 300)
    return scores, errors


def test_naive_takes_lowest_passing_threshold() -> None:
    s, e = _toy()
    res = select_naive(s, e, alpha=0.05, grid=default_grid())
    assert res.threshold is not None
    assert 0.5 < res.threshold <= 0.9  # excludes the noisy half
    assert res.coverage == 0.5


def test_certified_is_never_more_lenient_than_naive() -> None:
    s, e = _toy()
    naive = select_naive(s, e, 0.05)
    cert = select_certified(s, e, 0.05, 0.1)
    assert naive.threshold is not None and cert.threshold is not None
    assert cert.threshold >= naive.threshold
    assert cert.bound is not None and cert.bound <= 0.05


def test_certified_refuses_when_nothing_is_safe() -> None:
    s = np.linspace(0, 1, 500, dtype=np.float64)
    e = np.ones(500, dtype=np.float64)  # student always wrong
    assert select_certified(s, e, 0.05, 0.1).threshold is None
    assert select_naive(s, e, 0.05).threshold is None


def test_certified_declines_with_too_little_data() -> None:
    s = np.array([0.99] * 20, dtype=np.float64)
    e = np.zeros(20, dtype=np.float64)
    # 20 clean samples cannot certify a 1% risk target at delta=0.1
    assert select_certified(s, e, 0.01, 0.1).threshold is None


def test_certify_once_is_all_or_nothing() -> None:
    s, e = _toy()
    ok = certify_once(s[::2], e[::2], s[1::2], e[1::2], 0.05, 0.1)
    assert ok.threshold is not None
    bad_errors = np.ones_like(e[1::2])
    fail = certify_once(s[::2], e[::2], s[1::2], bad_errors, 0.05, 0.1)
    assert fail.threshold is None


def test_risk_coverage_and_metrics() -> None:
    s, e = _toy()
    cov, risk = risk_coverage(s, e, np.array([0.0, 0.8, 0.95]))
    assert cov.tolist() == [1.0, 0.5, 0.0]
    assert risk[1] == 2 / 400
    assert np.isnan(risk[2])
    assert 0.0 <= aurc(s, e) <= 1.0
    perfect = ece(np.array([0.5] * 4), np.array([1.0, 0.0, 1.0, 0.0]))
    assert perfect == 0.0  # confidence 0.5, accuracy 0.5
    overconfident = ece(np.array([0.9] * 4), np.array([1.0, 0.0, 1.0, 0.0]))
    assert abs(overconfident - 0.4) < 1e-9


def test_strict_sequence_pitfall_and_fixes() -> None:
    # 37 perfectly confident items (0 errors) then 1,963 mostly-correct items at lower confidence.
    s = np.array([0.995] * 37 + [0.8] * 1963)
    e = np.array([0.0] * 37 + [1.0] * 39 + [0.0] * 1924)
    # the strict-start walk stops at the first (tiny) threshold: 0/37 has an upper bound > 5%
    assert select_certified(s, e, 0.05, 0.1).threshold is None
    # the fixes reach the large, safe region (risk 39/1963 ~ 2%)
    bon = select_bonferroni(s, e, 0.05, 0.1)
    assert bon.threshold is not None and bon.coverage > 0.9
    assert bon.bound is not None and bon.bound <= 0.05
    spl = select_split_sequence(s, e, 0.05, 0.1, seed=3)
    assert spl.threshold is not None and spl.coverage > 0.9


def test_coarse_grid_is_a_subset_of_default_grid() -> None:
    fine = set(np.round(default_grid(), 6))
    assert all(round(float(t), 6) in fine for t in coarse_grid())
    assert len(coarse_grid()) == 32


def test_split_sequence_declines_without_a_safe_start() -> None:
    s = np.linspace(0, 1, 400, dtype=np.float64)
    assert select_split_sequence(s, np.ones(400), 0.05, 0.1).threshold is None


def test_binomial_pvalue_matches_clopper_pearson_duality() -> None:
    for n in (30, 120, 800):
        for k in (0, 1, 3, 10):
            for alpha, level in ((0.05, 0.01), (0.1, 0.02), (0.02, 0.003)):
                p = float(binom.cdf(k, n, alpha))
                # reject H0 (risk > alpha) iff the CP upper bound at that level is <= alpha
                assert (p <= level) == (cp_upper(k, n, level) <= alpha), (n, k, alpha, level)


def test_holm_is_at_least_as_lenient_as_bonferroni() -> None:
    rng = np.random.default_rng(0)
    for _ in range(60):
        n = int(rng.integers(300, 3000))
        scores = rng.beta(6, 1.5, size=n)
        errors = (rng.random(n) >= 0.5 + 0.5 * scores**2).astype(np.float64)
        bon = select_bonferroni(scores, errors, 0.08, 0.1)
        holm = select_holm(scores, errors, 0.08, 0.1)
        if bon.threshold is not None:
            assert holm.threshold is not None
            assert holm.threshold <= bon.threshold + 1e-12


def test_wilson_bound_properties_and_baselines() -> None:
    assert wilson_upper(0, 0, 0.1) == 1.0
    assert 5 / 100 < wilson_upper(5, 100, 0.05) < cp_upper(5, 100, 0.05)
    s, e = _toy()
    assert select_wilson(s, e, 0.05, 0.1).threshold is not None
    safe = select_safety_factor(s, e, 0.05, 0.8)
    naive = select_naive(s, e, 0.05)
    assert safe.threshold is not None and naive.threshold is not None
    assert safe.threshold >= naive.threshold
