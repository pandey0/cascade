"""Exact binomial (Clopper-Pearson) confidence bounds."""

from __future__ import annotations

from scipy.stats import beta


def cp_upper(errors: int, n: int, delta: float) -> float:
    """One-sided upper confidence bound on an error rate.

    With probability >= 1 - delta (over the sample), the true error rate is <= the result,
    assuming ``n`` independent draws. ``n == 0`` gives the vacuous bound 1.0.
    """
    _check(errors, n, delta)
    if n == 0 or errors >= n:
        return 1.0
    return float(beta.ppf(1.0 - delta, errors + 1, n - errors))


def cp_lower(successes: int, n: int, delta: float) -> float:
    """One-sided lower confidence bound on a success rate (``n == 0`` gives 0.0)."""
    _check(successes, n, delta)
    if n == 0 or successes <= 0:
        return 0.0
    if successes >= n:
        return float(delta ** (1.0 / n))
    return float(beta.ppf(delta, successes, n - successes + 1))


def _check(k: int, n: int, delta: float) -> None:
    if n < 0 or k < 0 or k > n:
        msg = f"need 0 <= k <= n, got k={k}, n={n}"
        raise ValueError(msg)
    if not 0.0 < delta < 1.0:
        msg = f"delta must be in (0, 1), got {delta}"
        raise ValueError(msg)
