"""Drift handling: an anytime-valid risk monitor and rolling recalibration on audit labels.

Monitor: the predictable plug-in empirical-Bernstein confidence sequence (PrPl-EB, Theorem 2 of
Waudby-Smith & Ramdas, "Estimating means of bounded random variables by betting", arXiv
2010.09686; formulas read from the paper). It is valid at all times simultaneously, so
repeated peeking does not inflate false alarms, unlike a fixed-sample interval re-evaluated each
step. It targets a *constant* mean; under a real change in risk it is used as a change alarm,
not as a certificate for the post-change distribution.

Recalibration: a sliding window of randomly audited decisions is the calibration set for a
fresh Holm certification. Each recalibration has its own delta; the guarantee over many
recalibrations is NOT family-wise controlled (see ADR 0005) and is reported empirically.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from cascade.gates import GateResult, coarse_grid, select_holm, select_naive

FloatArray = NDArray[np.float64]


class RiskMonitor:
    """PrPl-EB confidence sequence for the mean of [0, 1]-valued observations."""

    def __init__(self, alpha: float = 0.05, c: float = 0.75) -> None:
        if not (0.0 < alpha < 1.0 and 0.0 < c < 1.0):
            msg = "alpha and c must be in (0, 1)"
            raise ValueError(msg)
        self.alpha = alpha
        self.c = c
        self.t = 0
        self._sum_x = 0.0
        self._sum_dev2 = 0.0  # sum (x_i - mu_hat_i)^2 with the regularised running mean
        self._sum_lam = 0.0
        self._sum_lam_x = 0.0
        self._sum_v_psi = 0.0
        self._lo = 0.0
        self._hi = 1.0
        self.raw_lower = 0.0

    @staticmethod
    def _psi_e(lam: float) -> float:
        return (-math.log(1.0 - lam) - lam) / 4.0

    def update(self, x: float) -> tuple[float, float]:
        """Add one observation; return the running-intersection interval ``(lower, upper)``."""
        if not 0.0 <= x <= 1.0:
            msg = "observation must be in [0, 1]"
            raise ValueError(msg)
        t = self.t + 1
        # predictable quantities use data up to t - 1
        mu_prev = (0.5 + self._sum_x) / t  # mu_hat_{t-1}
        var_prev = (0.25 + self._sum_dev2) / t  # sigma_hat_{t-1}^2 (the "4 *" is folded into v_i)
        sigma2_prev = 4.0 * var_prev if t > 1 else 1.0
        lam = min(
            math.sqrt(
                2.0 * math.log(2.0 / self.alpha) / (max(sigma2_prev, 1e-12) * t * math.log(1 + t))
            ),
            self.c,
        )
        v = 4.0 * (x - mu_prev) ** 2
        self._sum_lam += lam
        self._sum_lam_x += lam * x
        self._sum_v_psi += v * self._psi_e(lam)
        center = self._sum_lam_x / self._sum_lam
        width = (math.log(2.0 / self.alpha) + self._sum_v_psi) / self._sum_lam
        self.raw_lower = center - width  # valid at every t; robust to a later change in the mean
        self._lo = max(self._lo, center - width)
        self._hi = min(self._hi, center + width)
        # update regularised moments with x_t for the next step
        self._sum_x += x
        mu_now = (0.5 + self._sum_x) / (t + 1)
        self._sum_dev2 += (x - mu_now) ** 2
        self.t = t
        return self._lo, self._hi

    @property
    def lower(self) -> float:
        """Running-intersection lower bound (assumes a constant mean)."""
        return self._lo


class WindowedZTest:
    """Naive baseline: normal-approximation one-sided test on the last ``size`` observations,
    re-evaluated at every step (so repeated peeking inflates its false-alarm rate)."""

    def __init__(self, size: int = 200, z: float = 1.645) -> None:
        self.buf: deque[float] = deque(maxlen=size)
        self.z = z

    def update(self, x: float) -> float:
        self.buf.append(x)
        n = len(self.buf)
        if n < 20:
            return 0.0
        p = sum(self.buf) / n
        return p - self.z * math.sqrt(max(p * (1 - p), 1e-12) / n)


@dataclass(frozen=True)
class DriftConfig:
    alpha: float = 0.05
    delta: float = 0.1
    audit_rate: float = 0.05
    window_labels: int = 400  # audited decisions kept for recalibration
    recal_every: int = 200  # decisions between recalibrations
    min_labels: int = 100  # below this, do not certify (escalate all)
    initial_labels: int = 1000  # audited labels available before the stream starts
    block: int = 500  # decisions per reporting block


def _gate(policy: str, s: FloatArray, e: FloatArray, cfg: DriftConfig) -> GateResult | None:
    if len(s) < cfg.min_labels:
        return None
    if policy == "rolling_holm":
        return select_holm(s, e, cfg.alpha, cfg.delta)
    return select_naive(s, e, cfg.alpha, coarse_grid())


def simulate_stream(  # noqa: PLR0917
    pre: tuple[FloatArray, FloatArray],
    post: tuple[FloatArray, FloatArray],
    n_pre: int,
    n_post: int,
    policy: str,
    cfg: DriftConfig,
    seed: int,
) -> dict[str, Any]:
    """Serve ``n_pre`` decisions from the pre-shift pool then ``n_post`` from the post-shift pool.

    ``pre``/``post`` are (scores, errors) pools; items are drawn with replacement. Policies:
    ``static_holm`` (certify once on the initial audit set, never update), ``rolling_naive``
    and ``rolling_holm`` (recalibrate on the sliding audit window). Error = student != teacher
    on accepted items; escalated items cost a teacher call and count as error 0.
    Returns per-block accepted-risk and coverage, plus alarm times for both monitors.
    """
    rng = np.random.default_rng(seed)
    ps, pe = pre
    qs, qe = post
    init = rng.choice(len(ps), size=cfg.initial_labels, replace=True)
    win_s: deque[float] = deque(ps[init][-cfg.window_labels :], maxlen=cfg.window_labels)
    win_e: deque[float] = deque(pe[init][-cfg.window_labels :], maxlen=cfg.window_labels)
    first = _gate(
        "rolling_holm" if policy != "rolling_naive" else policy,
        ps[init],
        pe[init],
        cfg,
    )
    thr = first.threshold if first else None
    monitor = RiskMonitor(cfg.alpha)
    ztest = WindowedZTest()
    alarm_cs = alarm_z = None
    blocks: list[dict[str, float]] = []
    acc_err = acc_n = 0
    total_n = 0
    n_total = n_pre + n_post
    for step in range(n_total):
        in_post = step >= n_pre
        s_pool, e_pool = (qs, qe) if in_post else (ps, pe)
        i = int(rng.integers(len(s_pool)))
        s, e = float(s_pool[i]), float(e_pool[i])
        accepted = thr is not None and s >= thr
        total_n += 1
        if accepted:
            acc_n += 1
            acc_err += int(e)
        audited = rng.random() < cfg.audit_rate
        if audited:
            win_s.append(s)
            win_e.append(e)
            if accepted:  # audited accepted items feed the monitors
                monitor.update(e)
                if alarm_cs is None and monitor.raw_lower > cfg.alpha:
                    alarm_cs = step
                if alarm_z is None and ztest.update(e) > cfg.alpha:
                    alarm_z = step
        if policy != "static_holm" and (step + 1) % cfg.recal_every == 0:
            g = _gate(policy, np.array(win_s), np.array(win_e), cfg)
            thr = g.threshold if g else None
        if (step + 1) % cfg.block == 0:
            blocks.append(
                {
                    "end": float(step + 1),
                    "post": float(in_post),
                    "risk": acc_err / acc_n if acc_n else float("nan"),
                    "coverage": acc_n / total_n,
                }
            )
            acc_err = acc_n = total_n = 0
    return {"blocks": blocks, "alarm_cs": alarm_cs, "alarm_z": alarm_z, "n_pre": n_pre}


def summarise_trials(trials: list[dict[str, Any]], alpha: float) -> dict[str, float]:
    """Aggregate: post-shift risk/coverage, violation fraction, recovery and alarm statistics."""
    post_risk: list[float] = []
    post_cov: list[float] = []
    viol: list[float] = []
    recover: list[float] = []
    false_cs = false_z = 0
    delay_cs: list[int] = []
    delay_z: list[int] = []
    for t in trials:
        n_pre = t["n_pre"]
        pre_blocks = [b for b in t["blocks"] if not b["post"]]
        post_blocks = [b for b in t["blocks"] if b["post"]]
        post_risk.extend(b["risk"] for b in post_blocks if not math.isnan(b["risk"]))
        post_cov.extend(b["coverage"] for b in post_blocks)
        viol.extend(float(b["risk"] > alpha) for b in post_blocks if not math.isnan(b["risk"]))
        ok = [b for b in post_blocks if math.isnan(b["risk"]) or b["risk"] <= alpha]
        recover.append(ok[0]["end"] - n_pre if ok else float("inf"))
        del pre_blocks
        for key, delays in (("alarm_cs", delay_cs), ("alarm_z", delay_z)):
            a = t[key]
            if a is not None and a < n_pre:
                if key == "alarm_cs":
                    false_cs += 1
                else:
                    false_z += 1
            elif a is not None:
                delays.append(a - n_pre)
    n = len(trials)
    return {
        "post_mean_risk": float(np.mean(post_risk)) if post_risk else float("nan"),
        "post_mean_coverage": float(np.mean(post_cov)) if post_cov else float("nan"),
        "post_block_violation_rate": float(np.mean(viol)) if viol else float("nan"),
        "median_recovery_decisions": float(np.median(recover)),
        "false_alarm_cs": false_cs / n,
        "false_alarm_z": false_z / n,
        "detect_rate_cs": len(delay_cs) / n,
        "detect_rate_z": len(delay_z) / n,
        "median_delay_cs": float(np.median(delay_cs)) if delay_cs else float("nan"),
        "median_delay_z": float(np.median(delay_z)) if delay_z else float("nan"),
    }
