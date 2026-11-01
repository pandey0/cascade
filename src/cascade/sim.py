"""Experiment 0: do naive gates violate their target? (synthetic scores, no API, no data).

The cheap model's confidence ``c`` is drawn from Beta(a, b); agreement with the teacher happens
with probability ``p(c) = min(cap, base + (1 - base) * c**gamma)``, which increases with
confidence. True risk and coverage of every threshold are computed by numerical integration, so
violations are measured against ground truth rather than another sample.

This is a controlled illustration of selection bias, NOT evidence about any real task.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import quad
from scipy.stats import beta as beta_dist

from cascade.gates import (
    GateResult,
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

FloatArray = NDArray[np.float64]
METHODS = (
    "naive",
    "safety80",
    "wilson",
    "certify_once",
    "strict_sequence",
    "bonferroni",
    "holm",
    "split_sequence",
)


@dataclass(frozen=True)
class SynthModel:
    a: float = 8.0
    b: float = 1.2
    base: float = 0.55
    gamma: float = 2.0
    cap: float = 0.999

    def p_agree(self, c: FloatArray | float) -> FloatArray | float:
        return np.minimum(self.cap, self.base + (1.0 - self.base) * np.power(c, self.gamma))

    def sample(self, n: int, rng: np.random.Generator) -> tuple[FloatArray, FloatArray]:
        scores = rng.beta(self.a, self.b, size=n)
        errors = (rng.random(n) >= self.p_agree(scores)).astype(np.float64)
        return scores, errors

    def true_curves(self, grid: FloatArray) -> tuple[FloatArray, FloatArray]:
        """Exact (coverage, risk) for each threshold in ``grid``."""
        cov = np.empty(len(grid))
        risk = np.empty(len(grid))
        for i, t in enumerate(grid):
            mass = 1.0 - beta_dist.cdf(t, self.a, self.b)
            cov[i] = mass
            if mass <= 1e-12:
                risk[i] = float("nan")
                continue
            num, _ = quad(
                lambda c: float(self.p_agree(c)) * beta_dist.pdf(c, self.a, self.b), t, 1.0
            )
            risk[i] = 1.0 - num / mass
        return cov, risk


def record_gate(
    res: GateResult, grid: FloatArray, cov_true: FloatArray, risk_true: FloatArray, alpha: float
) -> dict[str, float]:
    if res.threshold is None:
        return {"deployed": 0.0, "violation": 0.0, "coverage": 0.0, "risk": float("nan")}
    i = int(np.argmin(np.abs(grid - res.threshold)))
    return {
        "deployed": 1.0,
        "violation": float(risk_true[i] > alpha),
        "coverage": float(cov_true[i]),
        "risk": float(risk_true[i]),
    }


def summarise(acc: dict[str, list[dict[str, float]]], m: int, trials: int) -> list[dict[str, Any]]:
    """Aggregate per-trial records into one row per method."""
    rows: list[dict[str, Any]] = []
    for method, recs in acc.items():
        deployed = np.array([r["deployed"] for r in recs])
        viol = np.array([r["violation"] for r in recs])
        cov = np.array([r["coverage"] for r in recs])
        risks = np.array([r["risk"] for r in recs])
        rows.append(
            {
                "method": method,
                "m": m,
                "trials": trials,
                "deploy_rate": float(deployed.mean()),
                "violation_rate_all": float(viol.mean()),
                "violation_rate_deployed": (
                    float(viol.sum() / deployed.sum()) if deployed.sum() else float("nan")
                ),
                "mean_coverage": float(cov.mean()),
                "mean_true_risk_deployed": (
                    float(np.nanmean(risks)) if deployed.sum() else float("nan")
                ),
            }
        )
    return rows


def run_exp0(  # noqa: PLR0917
    sizes: list[int],
    trials: int,
    alpha: float,
    delta: float,
    seed: int = 0,
    model: SynthModel | None = None,
) -> list[dict[str, Any]]:
    """Compare naive, certify-once and certified fixed-sequence gates across calibration sizes."""
    model = SynthModel() if model is None else model
    grid = default_grid()
    cov_true, risk_true = model.true_curves(grid)
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for m in sizes:
        acc: dict[str, list[dict[str, float]]] = {name: [] for name in METHODS}
        for _ in range(trials):
            scores, errors = model.sample(m, rng)
            acc["naive"].append(
                record_gate(
                    select_naive(scores, errors, alpha, grid), grid, cov_true, risk_true, alpha
                )
            )
            acc["strict_sequence"].append(
                record_gate(
                    select_certified(scores, errors, alpha, delta, grid),
                    grid,
                    cov_true,
                    risk_true,
                    alpha,
                )
            )
            acc["safety80"].append(
                record_gate(
                    select_safety_factor(scores, errors, alpha, 0.8, grid),
                    grid,
                    cov_true,
                    risk_true,
                    alpha,
                )
            )
            acc["wilson"].append(
                record_gate(
                    select_wilson(scores, errors, alpha, delta, grid),
                    grid,
                    cov_true,
                    risk_true,
                    alpha,
                )
            )
            acc["holm"].append(
                record_gate(
                    select_holm(scores, errors, alpha, delta), grid, cov_true, risk_true, alpha
                )
            )
            acc["bonferroni"].append(
                record_gate(
                    select_bonferroni(scores, errors, alpha, delta),
                    grid,
                    cov_true,
                    risk_true,
                    alpha,
                )
            )
            acc["split_sequence"].append(
                record_gate(
                    select_split_sequence(
                        scores, errors, alpha, delta, grid, seed=int(rng.integers(2**31))
                    ),
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
                    certify_once(
                        scores[sel], errors[sel], scores[cert], errors[cert], alpha, delta, grid
                    ),
                    grid,
                    cov_true,
                    risk_true,
                    alpha,
                )
            )
        rows.extend(summarise(acc, m, trials))
    return rows


def to_markdown(rows: list[dict[str, Any]], alpha: float, delta: float) -> str:
    head = (
        f"Target risk alpha={alpha}, confidence delta={delta}. Synthetic scores (see sim.py).\n\n"
        "| method | m | deploy rate | violation rate (all trials) | violation (deployed) "
        "| mean coverage | mean true risk (deployed) |\n|---|---|---|---|---|---|---|\n"
    )
    body = "\n".join(
        f"| {r['method']} | {r['m']} | {r['deploy_rate']:.3f} | {r['violation_rate_all']:.3f} | "
        f"{r['violation_rate_deployed']:.3f} | {r['mean_coverage']:.3f} | "
        f"{r['mean_true_risk_deployed']:.4f} |"
        for r in rows
    )
    return head + body + "\n"
