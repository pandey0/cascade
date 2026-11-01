"""Gate evaluation on a fixed finite population (a held-out pool of real scores and errors).

The pool is treated as the population, so the true risk and coverage of every threshold are exact
for that population. Calibration sets are drawn from it without replacement. This is a
selection-procedure study on one fixed student; it says nothing about teacher noise or drift.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from cascade.gates import (
    certify_once,
    default_grid,
    select_bonferroni,
    select_certified,
    select_holm,
    select_naive,
    select_safety_factor,
    select_split_sequence,
    select_wilson,
)
from cascade.metrics import risk_coverage
from cascade.sim import METHODS, record_gate, summarise

FloatArray = NDArray[np.float64]


def run_pool_experiment(  # noqa: PLR0917
    scores: FloatArray,
    errors: FloatArray,
    sizes: list[int],
    trials: int,
    alpha: float,
    delta: float,
    seed: int = 0,
    eval_errors: FloatArray | None = None,
) -> list[dict[str, Any]]:
    """Compare naive, certify-once and certified gates over resampled calibration sets.

    Gates are fitted on calibration draws of ``errors``. True risk is computed on ``eval_errors``
    when given (e.g. gold-label errors while gates saw teacher-disagreement), else on ``errors``.
    """
    scores = np.asarray(scores, dtype=np.float64)
    errors = np.asarray(errors, dtype=np.float64)
    n = len(scores)
    grid = default_grid()
    truth = errors if eval_errors is None else np.asarray(eval_errors, dtype=np.float64)
    cov_true, risk_true = risk_coverage(scores, truth, grid)
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for m in sizes:
        if m > n // 2:
            msg = f"calibration size {m} exceeds half of the pool ({n})"
            raise ValueError(msg)
        acc: dict[str, list[dict[str, float]]] = {name: [] for name in METHODS}
        for _ in range(trials):
            idx = rng.choice(n, size=m, replace=False)
            s, e = scores[idx], errors[idx]
            acc["naive"].append(
                record_gate(select_naive(s, e, alpha, grid), grid, cov_true, risk_true, alpha)
            )
            acc["strict_sequence"].append(
                record_gate(
                    select_certified(s, e, alpha, delta, grid), grid, cov_true, risk_true, alpha
                )
            )
            acc["safety80"].append(
                record_gate(
                    select_safety_factor(s, e, alpha, 0.8, grid), grid, cov_true, risk_true, alpha
                )
            )
            acc["wilson"].append(
                record_gate(
                    select_wilson(s, e, alpha, delta, grid), grid, cov_true, risk_true, alpha
                )
            )
            acc["holm"].append(
                record_gate(select_holm(s, e, alpha, delta), grid, cov_true, risk_true, alpha)
            )
            acc["bonferroni"].append(
                record_gate(select_bonferroni(s, e, alpha, delta), grid, cov_true, risk_true, alpha)
            )
            acc["split_sequence"].append(
                record_gate(
                    select_split_sequence(s, e, alpha, delta, grid, seed=int(rng.integers(2**31))),
                    grid,
                    cov_true,
                    risk_true,
                    alpha,
                )
            )
            perm = rng.permutation(m)
            cut = int(0.8 * m)
            sel, cert = perm[:cut], perm[cut:]
            acc["certify_once"].append(
                record_gate(
                    certify_once(s[sel], e[sel], s[cert], e[cert], alpha, delta, grid),
                    grid,
                    cov_true,
                    risk_true,
                    alpha,
                )
            )
        rows.extend(summarise(acc, m, trials))
    return rows


def aggregate_pools(per_pool: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Merge per-pool result rows: means (original keys) plus min/max across pools."""
    keys = ("deploy_rate", "violation_rate_all", "mean_coverage")
    rows: list[dict[str, Any]] = []
    for i, base in enumerate(per_pool[0]):
        merged = dict(base)
        for k in keys:
            vals = np.array([p[i][k] for p in per_pool], dtype=np.float64)
            merged[k] = float(vals.mean())
            merged[f"{k}_min"] = float(np.min(vals))
            merged[f"{k}_max"] = float(np.max(vals))
        for k in ("violation_rate_deployed", "mean_true_risk_deployed"):
            vals = np.array([p[i][k] for p in per_pool], dtype=np.float64)
            merged[k] = float(np.nanmean(vals)) if not np.all(np.isnan(vals)) else float("nan")
        merged["pools"] = len(per_pool)
        rows.append(merged)
    return rows


def to_markdown_ranges(rows: list[dict[str, Any]], alpha: float, delta: float) -> str:
    """Markdown table with mean (min-max across pools) for the three headline metrics."""

    def cell(r: dict[str, Any], k: str) -> str:
        return f"{r[k]:.3f} ({r[k + '_min']:.3f}-{r[k + '_max']:.3f})"

    head = (
        f"Target risk alpha={alpha}, confidence delta={delta}. Real pools: {rows[0]['pools']} "
        "splits; cells show mean (min-max across splits).\n\n"
        "| method | m | deploy rate | violation rate (all draws) | mean coverage |\n"
        "|---|---|---|---|---|\n"
    )
    body = "\n".join(
        f"| {r['method']} | {r['m']} | {cell(r, 'deploy_rate')} | "
        f"{cell(r, 'violation_rate_all')} | {cell(r, 'mean_coverage')} |"
        for r in rows
    )
    return head + body + "\n"
