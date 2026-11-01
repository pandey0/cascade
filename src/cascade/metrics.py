"""Selective-classification and calibration metrics."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def risk_coverage(
    scores: FloatArray, errors: FloatArray, grid: FloatArray
) -> tuple[FloatArray, FloatArray]:
    """Empirical (coverage, risk) at each threshold in ``grid``.

    ``errors`` is 1.0 where the cheap model disagrees with the teacher, else 0.0. Accepting means
    ``score >= threshold``. Risk is NaN where nothing is accepted.
    """
    scores = np.asarray(scores, dtype=np.float64)
    errors = np.asarray(errors, dtype=np.float64)
    coverage = np.empty(len(grid))
    risk = np.empty(len(grid))
    for i, t in enumerate(grid):
        accepted = scores >= t
        n_acc = int(accepted.sum())
        coverage[i] = n_acc / len(scores) if len(scores) else 0.0
        risk[i] = float(errors[accepted].mean()) if n_acc else float("nan")
    return coverage, risk


def aurc(scores: FloatArray, errors: FloatArray) -> float:
    """Area under the risk-coverage curve (lower is better)."""
    order = np.argsort(-np.asarray(scores, dtype=np.float64), kind="stable")
    err = np.asarray(errors, dtype=np.float64)[order]
    cum_risk = np.cumsum(err) / np.arange(1, len(err) + 1)
    return float(cum_risk.mean())


def ece(confidence: FloatArray, correct: FloatArray, bins: int = 15) -> float:
    """Expected calibration error with equal-width bins."""
    confidence = np.asarray(confidence, dtype=np.float64)
    correct = np.asarray(correct, dtype=np.float64)
    edges = np.linspace(0.0, 1.0, bins + 1)
    idx = np.clip(np.digitize(confidence, edges[1:-1]), 0, bins - 1)
    total = 0.0
    for b in range(bins):
        mask = idx == b
        if mask.any():
            total += mask.mean() * abs(correct[mask].mean() - confidence[mask].mean())
    return float(total)
