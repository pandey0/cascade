"""Threshold-selection gates for a cheap-first cascade.

Terminology: a *score* is the cheap model's confidence; an *error* is 1 when the cheap model
disagrees with the teacher. A threshold ``t`` accepts inputs with ``score >= t``. The *risk* of
a threshold is P(error | accepted). Gates choose ``t`` to maximise coverage subject to
risk <= alpha.

Statistical note: a data-dependent threshold grid breaks the validity of fixed-sequence testing,
so grids here are fixed in advance (``default_grid``) and never derived from the sample.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.stats import binom, norm

from cascade.bounds import cp_lower, cp_upper

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class GateResult:
    """Outcome of a gate. ``threshold is None`` means: do not deploy the cheap path."""

    method: str
    threshold: float | None
    n_accepted: int
    coverage: float
    empirical_risk: float
    bound: float | None  # upper confidence bound on risk, when the method certifies one


def coarse_grid() -> FloatArray:
    """32 fixed thresholds (0.200 ... 0.975), a subset of ``default_grid()``."""
    return default_grid()[40:197:5]


def default_grid(low: float = 0.0, high: float = 1.0, steps: int = 201) -> FloatArray:
    """Fixed threshold grid, independent of any data."""
    return np.linspace(low, high, steps, dtype=np.float64)


def _stats(scores: FloatArray, errors: FloatArray, t: float) -> tuple[int, float, float]:
    accepted = scores >= t
    n_acc = int(accepted.sum())
    cov = n_acc / len(scores) if len(scores) else 0.0
    risk = float(errors[accepted].mean()) if n_acc else float("nan")
    return n_acc, cov, risk


def select_naive(
    scores: FloatArray,
    errors: FloatArray,
    alpha: float,
    grid: FloatArray | None = None,
    min_accept: int = 1,
) -> GateResult:
    """Pick the lowest threshold whose *empirical* risk on the same sample is <= alpha.

    This is the common 'held-out agreement gate'. It is optimistic: it selects the most
    favourable threshold on noisy data, so its guarantee does not transfer (winner's curse).
    """
    grid = default_grid() if grid is None else grid
    for t in grid:  # ascending: first passing threshold has the largest coverage
        n_acc, cov, risk = _stats(scores, errors, float(t))
        if n_acc >= min_accept and risk <= alpha:
            return GateResult("naive", float(t), n_acc, cov, risk, None)
    return GateResult("naive", None, 0, 0.0, float("nan"), None)


def select_certified(
    scores: FloatArray,
    errors: FloatArray,
    alpha: float,
    delta: float,
    grid: FloatArray | None = None,
) -> GateResult:
    """Strict-start fixed-sequence testing over a fixed grid (valid but low power).

    Walk thresholds from most to least confident; keep going while the Clopper-Pearson upper
    bound on risk stays <= alpha; stop at the first failure. With probability >= 1 - delta
    the returned threshold has true risk <= alpha, assuming i.i.d. calibration data.

    POWER PITFALL (found in experiment 1a): the strictest non-empty thresholds accept very few
    items, so even zero errors give a loose bound (for example 0 errors in 37 items has an upper
    bound of 6% at delta=0.1) and the walk stops before reaching thresholds with enough data.
    Kept as a baseline; prefer ``select_bonferroni`` or ``select_split_sequence``.
    """
    grid = default_grid() if grid is None else grid
    best: tuple[float, int, float, float, float] | None = None
    for t in grid[::-1]:  # descending: strictest first
        n_acc, cov, risk = _stats(scores, errors, float(t))
        if n_acc == 0:
            continue
        k = round(risk * n_acc)
        ub = cp_upper(k, n_acc, delta)
        if ub > alpha:
            break
        best = (float(t), n_acc, cov, risk, ub)
    if best is None:
        return GateResult("strict_sequence", None, 0, 0.0, float("nan"), None)
    t, n_acc, cov, risk, ub = best
    return GateResult("strict_sequence", t, n_acc, cov, risk, ub)


def certify_once(  # noqa: PLR0917
    sel_scores: FloatArray,
    sel_errors: FloatArray,
    cert_scores: FloatArray,
    cert_errors: FloatArray,
    alpha: float,
    delta: float,
    grid: FloatArray | None = None,
) -> GateResult:
    """Select with the naive rule on one split, then certify that single policy on a reserved split.

    Valid (the policy is fixed before the reserved split is touched) but all-or-nothing: if the
    bound fails there is no retry, so coverage is lost entirely. Models a 'reserve rows and
    certify the final policy once' design.
    """
    cand = select_naive(sel_scores, sel_errors, alpha, grid)
    if cand.threshold is None:
        return GateResult("certify_once", None, 0, 0.0, float("nan"), None)
    n_acc, cov, risk = _stats(cert_scores, cert_errors, cand.threshold)
    if n_acc == 0:
        return GateResult("certify_once", None, 0, 0.0, float("nan"), None)
    k = round(risk * n_acc)
    ub = cp_upper(k, n_acc, delta)
    if ub > alpha:
        return GateResult("certify_once", None, n_acc, cov, risk, ub)
    return GateResult("certify_once", cand.threshold, n_acc, cov, risk, ub)


def select_bonferroni(
    scores: FloatArray,
    errors: FloatArray,
    alpha: float,
    delta: float,
    grid: FloatArray | None = None,
) -> GateResult:
    """Test every point of a fixed coarse grid at level delta/K; take the most lenient pass.

    Valid by the union bound for any data-independent grid of K points: with probability
    >= 1 - delta, every threshold that passes has true risk <= alpha, so the chosen one does.
    No ordering assumption and no early stopping, at the price of a stricter per-test level.
    """
    grid = coarse_grid() if grid is None else grid
    level = delta / len(grid)
    best: tuple[float, int, float, float, float] | None = None
    for t in grid:  # ascending: first pass is the most lenient
        n_acc, cov, risk = _stats(scores, errors, float(t))
        if n_acc == 0:
            continue
        ub = cp_upper(round(risk * n_acc), n_acc, level)
        if ub <= alpha:
            best = (float(t), n_acc, cov, risk, ub)
            break
    if best is None:
        return GateResult("bonferroni", None, 0, 0.0, float("nan"), None)
    t, n_acc, cov, risk, ub = best
    return GateResult("bonferroni", t, n_acc, cov, risk, ub)


def select_split_sequence(  # noqa: PLR0917
    scores: FloatArray,
    errors: FloatArray,
    alpha: float,
    delta: float,
    grid: FloatArray | None = None,
    dev_fraction: float = 0.4,
    margin: float = 0.5,
    min_dev_accept: int = 30,
    seed: int = 0,
) -> GateResult:
    """Choose a safe starting threshold on a dev split, then fixed-sequence test on the rest.

    The dev part picks the most lenient grid threshold whose dev risk is <= ``margin * alpha``
    (with >= ``min_dev_accept`` accepted). The test part then walks from that threshold toward
    more lenient ones while the Clopper-Pearson upper bound stays <= alpha, and returns the last
    pass. The starting point and order depend only on the dev part, so the sequence is fixed
    before the test data is touched (valid at level delta). If the starting point itself fails,
    nothing is deployed. Uses only (1 - dev_fraction) of the data for the guarantee.
    """
    grid = default_grid() if grid is None else grid
    n = len(scores)
    perm = np.random.default_rng(seed).permutation(n)
    n_dev = int(dev_fraction * n)
    dev, test = perm[:n_dev], perm[n_dev:]
    start: float | None = None
    for t in grid:  # ascending: first pass is the most lenient
        n_acc, _, risk = _stats(scores[dev], errors[dev], float(t))
        if n_acc >= min_dev_accept and risk <= margin * alpha:
            start = float(t)
            break
    if start is None:
        return GateResult("split_sequence", None, 0, 0.0, float("nan"), None)
    best: tuple[float, int, float, float, float] | None = None
    for t in grid[grid >= 0][::-1]:  # strict to lenient
        if t > start:
            continue
        n_acc, cov, risk = _stats(scores[test], errors[test], float(t))
        if n_acc == 0:
            break
        ub = cp_upper(round(risk * n_acc), n_acc, delta)
        if ub > alpha:
            break
        best = (float(t), n_acc, cov, risk, ub)
    if best is None:
        return GateResult("split_sequence", None, 0, 0.0, float("nan"), None)
    t, n_acc, cov, risk, ub = best
    return GateResult("split_sequence", t, n_acc, cov, risk, ub)


def wilson_upper(errors: int, n: int, delta: float) -> float:
    """One-sided Wilson score upper bound on an error rate (approximate, not exact)."""
    if n <= 0:
        return 1.0
    z = float(norm.ppf(1.0 - delta))
    p = errors / n
    denom = 1.0 + z * z / n
    centre = p + z * z / (2.0 * n)
    radius = z * float(np.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)))
    return (centre + radius) / denom


def select_wilson(
    scores: FloatArray,
    errors: FloatArray,
    alpha: float,
    delta: float,
    grid: FloatArray | None = None,
) -> GateResult:
    """Lowest threshold whose Wilson upper bound is <= alpha, with NO multiplicity correction.

    A common practitioner fix (add a statistical margin). It still searches many thresholds on
    one sample, so its guarantee does not hold; included as an honest baseline.
    """
    grid = default_grid() if grid is None else grid
    for t in grid:  # ascending: most lenient first
        n_acc, cov, risk = _stats(scores, errors, float(t))
        if n_acc and wilson_upper(round(risk * n_acc), n_acc, delta) <= alpha:
            return GateResult("wilson", float(t), n_acc, cov, risk, None)
    return GateResult("wilson", None, 0, 0.0, float("nan"), None)


def select_safety_factor(
    scores: FloatArray,
    errors: FloatArray,
    alpha: float,
    factor: float = 0.8,
    grid: FloatArray | None = None,
) -> GateResult:
    """Naive selection against a tightened target ``factor * alpha`` (a rule-of-thumb margin)."""
    res = select_naive(scores, errors, alpha * factor, grid)
    return GateResult(
        "safety80", res.threshold, res.n_accepted, res.coverage, res.empirical_risk, None
    )


def select_holm(
    scores: FloatArray,
    errors: FloatArray,
    alpha: float,
    delta: float,
    grid: FloatArray | None = None,
) -> GateResult:
    """Holm step-down over a fixed coarse grid; take the most lenient rejected threshold.

    For each threshold, the exact one-sided binomial p-value of H0: risk > alpha is
    ``P(X <= k | n, alpha)`` (equivalent to the Clopper-Pearson test). Holm's procedure rejects
    in increasing p-value order while ``p_(i) <= delta / (K - i + 1)``, controlling the
    family-wise error at delta under arbitrary dependence and rejecting at least everything
    Bonferroni rejects. Thresholds with no accepted items have p = 1 and still count in K.
    """
    grid = coarse_grid() if grid is None else grid
    k_total = len(grid)
    stats = [_stats(scores, errors, float(t)) for t in grid]
    pvals = np.array(
        [
            float(binom.cdf(round(risk * n_acc), n_acc, alpha)) if n_acc else 1.0
            for n_acc, _, risk in stats
        ]
    )
    rejected: dict[int, float] = {}
    for rank, i in enumerate(np.argsort(pvals, kind="stable")):
        level = delta / (k_total - rank)
        if pvals[i] > level:
            break
        rejected[int(i)] = level
    if not rejected:
        return GateResult("holm", None, 0, 0.0, float("nan"), None)
    i = min(rejected)  # grid is ascending: lowest index = most lenient threshold
    n_acc, cov, risk = stats[i]
    ub = cp_upper(round(risk * n_acc), n_acc, rejected[i])
    return GateResult("holm", float(grid[i]), n_acc, cov, risk, ub)


def agreement_lower_bound(agreements: int, n: int, delta: float) -> float:
    """Convenience: one-sided lower bound on agreement (= 1 - risk upper bound)."""
    return cp_lower(agreements, n, delta)
