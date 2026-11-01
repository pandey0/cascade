"""Decision engine: student -> gate -> (teacher), with audit sampling, drift monitoring and
rolling recalibration.

Only uniformly random audits (or every item in shadow mode) are stored for calibration:
escalated items are selected by low confidence, and mixing them in would bias the risk
estimate at thresholds below the current one. Pure Python and injectable, so it is testable
without a network.

Failure policy (documented in docs/runbook.md): if the teacher is needed but fails or times
out, ``fail_open=True`` serves the student's best guess marked ``degraded``; ``False`` raises
:class:`TeacherUnavailableError` (the HTTP layer returns 503).
"""

from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from cascade.drift import RiskMonitor
from cascade.gates import select_holm
from cascade.store import AuditStore
from cascade.teacher import TeacherResponse

FloatArray = NDArray[np.float64]


class Student(Protocol):
    def predict_with_confidence(self, x: FloatArray) -> tuple[NDArray[np.str_], FloatArray]: ...


class TeacherUnavailableError(RuntimeError):
    """The teacher was needed but did not answer in time (or failed) and fail_open is off."""


@dataclass
class EngineConfig:
    decision: str
    alpha: float
    delta: float = 0.1
    audit_rate: float = 0.05
    shadow: bool = False  # True: always serve the teacher; student only recorded
    window_labels: int = 1000
    recal_every: int = 250  # audited labels between recalibrations
    min_labels: int = 100
    teacher_timeout_s: float = 10.0
    fail_open: bool = True
    seed: int | None = None


@dataclass(frozen=True)
class Decision:
    label: str
    path: str  # "cheap" | "teacher" | "shadow" | "cheap_degraded"
    confidence: float
    threshold: float | None
    audited: bool = False
    cost_usd: float = 0.0


@dataclass
class EngineStats:
    decisions: int = 0
    teacher_calls: int = 0
    teacher_errors: int = 0
    audits: int = 0
    spent_usd: float = 0.0
    recalibrations: int = 0
    drift_alarm: bool = False
    risk_lower: float = 0.0
    thresholds: list[float | None] = field(default_factory=list)


class Engine:
    def __init__(  # noqa: PLR0917
        self,
        cfg: EngineConfig,
        embed: Callable[[str], FloatArray],
        student: Student,
        teacher: Callable[[str], TeacherResponse],
        store: AuditStore,
        threshold: float | None,
        pool: ThreadPoolExecutor | None = None,
    ) -> None:
        self.cfg = cfg
        self._embed = embed
        self._student = student
        self._teacher = teacher
        self._store = store
        self.threshold = threshold
        self.stats = EngineStats(thresholds=[threshold])
        self._monitor = RiskMonitor(cfg.alpha)
        self._rng = random.Random(cfg.seed)  # noqa: S311  (sampling, not security)
        self._lock = threading.Lock()
        self._pool = pool or ThreadPoolExecutor(max_workers=8)
        self._owns_pool = pool is None
        self._since_recal = 0

    # -- teacher with timeout ------------------------------------------------
    def _call_teacher(self, text: str) -> TeacherResponse:
        with self._lock:
            self.stats.teacher_calls += 1
        future = self._pool.submit(self._teacher, text)
        try:
            resp = future.result(timeout=self.cfg.teacher_timeout_s)
        except (FuturesTimeout, Exception) as exc:
            future.cancel()
            with self._lock:
                self.stats.teacher_errors += 1
            raise TeacherUnavailableError(type(exc).__name__) from exc
        with self._lock:
            self.stats.spent_usd += resp.cost_usd
        return resp

    # -- main path -----------------------------------------------------------
    def decide(self, text: str) -> Decision:
        x = self._embed(text).reshape(1, -1)
        labels, conf = self._student.predict_with_confidence(x)
        student_label, c = str(labels[0]), float(conf[0])
        thr = self.threshold
        accepted = thr is not None and c >= thr
        with self._lock:
            self.stats.decisions += 1
        audited = self._rng.random() < self.cfg.audit_rate

        if self.cfg.shadow or not accepted or audited:
            try:
                t = self._call_teacher(text)
            except TeacherUnavailableError:
                if self.cfg.shadow or accepted:  # a cheap answer exists; just skip the audit
                    return Decision(
                        student_label, "cheap_degraded" if not accepted else "cheap", c, thr
                    )
                if self.cfg.fail_open:
                    return Decision(student_label, "cheap_degraded", c, thr)
                raise
            if audited or self.cfg.shadow:  # only uniform samples feed calibration (unbiased)
                self._record(text, c, student_label, t.label, accepted)
            if self.cfg.shadow:
                return Decision(t.label, "shadow", c, thr, True, t.cost_usd)
            if accepted:  # audited cheap-path item: serve the cheap answer, label is for monitoring
                return Decision(student_label, "cheap", c, thr, True, t.cost_usd)
            return Decision(t.label, "teacher", c, thr, audited, t.cost_usd)
        return Decision(student_label, "cheap", c, thr)

    # -- audit + recalibration + drift --------------------------------------
    def _record(self, text: str, conf: float, student: str, teacher: str, accepted: bool) -> None:
        self._store.add_audit(self.cfg.decision, text, conf, student, teacher, accepted)
        with self._lock:
            self.stats.audits += 1
            self._since_recal += 1
            if accepted:
                self._monitor.update(float(student != teacher))
                self.stats.risk_lower = self._monitor.raw_lower
                self.stats.drift_alarm = self._monitor.raw_lower > self.cfg.alpha
            due = self._since_recal >= self.cfg.recal_every
        if due:
            self.recalibrate()

    def recalibrate(self) -> float | None:
        """Re-certify the threshold on the sliding window of audited decisions (Holm)."""
        conf, err = self._store.recent(self.cfg.decision, self.cfg.window_labels)
        with self._lock:
            self._since_recal = 0
            if len(conf) < self.cfg.min_labels:
                return self.threshold
            result = select_holm(conf, err, self.cfg.alpha, self.cfg.delta)
            self.threshold = result.threshold
            self.stats.recalibrations += 1
            self.stats.thresholds.append(result.threshold)
            return self.threshold

    def close(self) -> None:
        if self._owns_pool:
            self._pool.shutdown(wait=False, cancel_futures=True)


def now() -> float:
    return time.time()
