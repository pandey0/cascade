"""Leakage-aware data splitting."""

from __future__ import annotations

import re
from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

IntArray = NDArray[np.int64]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def three_way_split(
    texts: Sequence[str], fractions: tuple[float, float, float] = (0.6, 0.2, 0.2), seed: int = 0
) -> tuple[IntArray, IntArray, IntArray]:
    """Split into train / calibration / audit-test, keeping duplicate texts in the same split.

    Duplicates (after whitespace/case normalisation) are grouped so near-identical inputs
    cannot leak between the student's training data and the calibration or test partitions.
    """
    if abs(sum(fractions) - 1.0) > 1e-9 or min(fractions) <= 0:
        msg = "fractions must be positive and sum to 1"
        raise ValueError(msg)
    groups: dict[str, list[int]] = {}
    for i, t in enumerate(texts):
        groups.setdefault(normalize(t), []).append(i)
    keys = sorted(groups)
    rng = np.random.default_rng(seed)
    rng.shuffle(keys)
    n = len(texts)
    bounds = (fractions[0] * n, (fractions[0] + fractions[1]) * n)
    parts: list[list[int]] = [[], [], []]
    placed = 0
    for k in keys:
        slot = 0 if placed < bounds[0] else (1 if placed < bounds[1] else 2)
        parts[slot].extend(groups[k])
        placed += len(groups[k])
    return tuple(np.array(sorted(p), dtype=np.int64) for p in parts)  # type: ignore[return-value]


def two_way_split(
    texts: Sequence[str], first_fraction: float = 0.5, seed: int = 0
) -> tuple[IntArray, IntArray]:
    """Split into two parts, keeping duplicate (normalised) texts together."""
    if not 0.0 < first_fraction < 1.0:
        msg = "first_fraction must be in (0, 1)"
        raise ValueError(msg)
    groups: dict[str, list[int]] = {}
    for i, t in enumerate(texts):
        groups.setdefault(normalize(t), []).append(i)
    keys = sorted(groups)
    rng = np.random.default_rng(seed)
    rng.shuffle(keys)
    cut = first_fraction * len(texts)
    first: list[int] = []
    second: list[int] = []
    for k in keys:
        (first if len(first) < cut else second).extend(groups[k])
    return np.array(sorted(first), dtype=np.int64), np.array(sorted(second), dtype=np.int64)
