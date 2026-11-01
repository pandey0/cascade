"""Decision engine: student -> gate -> (teacher), with audit sampling, drift monitoring and
rolling recalibration.

Only uniformly random audits (or every item in shadow mode) are stored for calibration:
escalated items are selected by low confidence, and mixing them in would bias the risk
estimate at thresholds below the current one. Pure Python and injectable, so it is testable
without a network.

Failure policy (documented in docs/runbook.md): if the teacher is needed but fails or times
out, ``fail_open=True`` serves the student's best guess marked ``degraded``; ``False`` raises
:class:`TeacherUnavailableError` (the HTTP layer returns 503).

Request path vs background (changed after two measured defects, see docs/critique.md):

* A request waits for the teacher only when the teacher's answer is what it returns. A confident
  request that happens to be audited is answered at once; the teacher call, the database write
  and any re-tuning of the cutoff run on background audit workers behind a bounded queue. When the
  queue is full the audit is dropped and counted (the drop decision does not depend on the
  request's content, so the audited sample stays uniform).
* Request-path teacher calls use a pool as large as the concurrency limit, hold a slot until the
  call really ends (not until the caller gave up), and fail fast when every slot is stuck instead
  of queueing behind stalled calls. The teacher adapters enforce the timeout in their HTTP client
  so that stalled calls do end.
"""

from __future__ import annotations

import logging
import queue
import random
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from cascade.drift import RiskMonitor
from cascade.gates import select_holm
from cascade.store import AuditStore
from cascade.teacher import TeacherResponse

FloatArray = NDArray[np.float64]
log = logging.getLogger("cascade")


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
    teacher_workers: int = 32  # concurrent request-path teacher calls (>= gateway concurrency)
    audit_workers: int = 2  # background threads that label and record audits
    audit_queue_size: int = 256  # pending audits; beyond this they are dropped and counted


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
    audits_dropped: int = 0
    audit_errors: int = 0
    spent_usd: float = 0.0
    recalibrations: int = 0
    drift_alarm: bool = False
    risk_lower: float = 0.0
    thresholds: list[float | None] = field(default_factory=list)


@dataclass(frozen=True)
class _AuditJob:
    text: str
    conf: float
    student_label: str
    accepted: bool
    teacher_label: str | None  # None: the background worker must still ask the teacher


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
        self._pool = pool or ThreadPoolExecutor(
            max_workers=cfg.teacher_workers, thread_name_prefix="teacher"
        )
        self._owns_pool = pool is None
        self._slots = threading.BoundedSemaphore(cfg.teacher_workers)
        self._in_flight = 0
        self._since_recal = 0
        self._audit_q: queue.Queue[_AuditJob | None] = queue.Queue(maxsize=cfg.audit_queue_size)
        self._audit_threads = [
            threading.Thread(target=self._audit_worker, name=f"audit-{i}", daemon=True)
            for i in range(cfg.audit_workers)
        ]
        for t in self._audit_threads:
            t.start()

    # -- observability helpers -------------------------------------------------
    @property
    def audit_queue_depth(self) -> int:
        return self._audit_q.qsize()

    @property
    def teacher_in_flight(self) -> int:
        with self._lock:
            return self._in_flight

    # -- request-path teacher call ---------------------------------------------
    def _call_teacher(self, text: str) -> TeacherResponse:
        """Ask the teacher for a request that needs its answer (fails fast if saturated)."""
        if not self._slots.acquire(blocking=False):
            with self._lock:
                self.stats.teacher_errors += 1
            raise TeacherUnavailableError("saturated")
        with self._lock:
            self.stats.teacher_calls += 1
            self._in_flight += 1
        try:
            future: Future[TeacherResponse] = self._pool.submit(self._teacher, text)
        except Exception:
            self._release_slot()
            raise
        future.add_done_callback(lambda _f: self._release_slot())  # freed when the call ends
        try:
            resp = future.result(timeout=self.cfg.teacher_timeout_s)
        except Exception as exc:
            future.cancel()
            with self._lock:
                self.stats.teacher_errors += 1
            raise TeacherUnavailableError(type(exc).__name__) from exc
        with self._lock:
            self.stats.spent_usd += resp.cost_usd
        return resp

    def _release_slot(self) -> None:
        with self._lock:
            self._in_flight -= 1
        self._slots.release()

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

        if not (self.cfg.shadow or not accepted):
            if audited:  # confident request picked for audit: answer now, label in the background
                self._enqueue(_AuditJob(text, c, student_label, accepted, None))
                return Decision(student_label, "cheap", c, thr, True)
            return Decision(student_label, "cheap", c, thr)

        # the teacher's answer is what this request returns
        try:
            t = self._call_teacher(text)
        except TeacherUnavailableError:
            if self.cfg.shadow or accepted:  # a cheap answer exists
                return Decision(
                    student_label, "cheap_degraded" if not accepted else "cheap", c, thr
                )
            if self.cfg.fail_open:
                return Decision(student_label, "cheap_degraded", c, thr)
            raise
        if audited or self.cfg.shadow:  # only uniform samples feed calibration (unbiased)
            self._enqueue(_AuditJob(text, c, student_label, accepted, t.label))
        if self.cfg.shadow:
            return Decision(t.label, "shadow", c, thr, True, t.cost_usd)
        return Decision(t.label, "teacher", c, thr, audited, t.cost_usd)

    # -- background audits ------------------------------------------------------
    def _enqueue(self, job: _AuditJob) -> None:
        try:
            self._audit_q.put_nowait(job)
        except queue.Full:
            with self._lock:
                self.stats.audits_dropped += 1

    def _audit_worker(self) -> None:
        while True:
            job = self._audit_q.get()
            try:
                if job is None:
                    return
                self._process_audit(job)
            except Exception:
                with self._lock:
                    self.stats.audit_errors += 1
                log.warning("audit failed", exc_info=True)
            finally:
                self._audit_q.task_done()

    def _process_audit(self, job: _AuditJob) -> None:
        teacher_label = job.teacher_label
        if teacher_label is None:
            with self._lock:
                self.stats.teacher_calls += 1
            resp = self._teacher(job.text)  # adapters enforce their own timeout
            with self._lock:
                self.stats.spent_usd += resp.cost_usd
            teacher_label = resp.label
        self._record(job.text, job.conf, job.student_label, teacher_label, job.accepted)

    def flush_audits(self, timeout: float = 5.0) -> bool:
        """Wait until queued audits are processed (tests, shutdown). True if the queue drained."""
        end = time.monotonic() + timeout
        while self._audit_q.unfinished_tasks > 0:
            if time.monotonic() > end:
                return False
            time.sleep(0.005)
        return True

    # -- audit recording, recalibration, drift ---------------------------------
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
        result = select_holm(conf, err, self.cfg.alpha, self.cfg.delta)  # computed outside the lock
        with self._lock:
            self.threshold = result.threshold
            self.stats.recalibrations += 1
            self.stats.thresholds.append(result.threshold)
            return self.threshold

    def close(self, drain_timeout: float = 5.0) -> None:
        """Drain pending audits (bounded), stop the background workers and the teacher pool."""
        self.flush_audits(drain_timeout)
        for _ in self._audit_threads:
            try:
                self._audit_q.put_nowait(None)
            except queue.Full:
                break
        for t in self._audit_threads:
            t.join(timeout=1.0)
        if self._owns_pool:
            self._pool.shutdown(wait=False, cancel_futures=True)


def now() -> float:
    return time.time()
