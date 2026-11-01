import sqlite3
import threading
import time
from pathlib import Path

import pytest

from cascade.engine import TeacherUnavailableError
from cascade.teacher import TeacherResponse

from .fakes import make_engine, make_teacher


def test_cheap_above_threshold_and_teacher_below(tmp_path: Path) -> None:
    calls = []
    inner = make_teacher("t")

    def spy(text: str):  # type: ignore[no-untyped-def]
        calls.append(text)
        return inner(text)

    eng, _ = make_engine(tmp_path, threshold=0.8, teacher=spy)
    hi = eng.decide("x c=0.95")
    lo = eng.decide("y c=0.40")
    assert (hi.label, hi.path) == ("s", "cheap") and calls == ["y c=0.40"]
    assert (lo.label, lo.path) == ("t", "teacher")
    assert eng.stats.teacher_calls == 1 and eng.stats.spent_usd == pytest.approx(0.001)


def test_no_threshold_escalates_everything(tmp_path: Path) -> None:
    eng, _ = make_engine(tmp_path, threshold=None)
    assert eng.decide("x c=0.99").path == "teacher"


def test_shadow_serves_teacher_and_records_everything(tmp_path: Path) -> None:
    eng, store = make_engine(tmp_path, shadow=True, recal_every=10_000)
    d = eng.decide("x c=0.95")
    assert (d.label, d.path, d.audited) == ("t", "shadow", True)
    assert eng.flush_audits() and store.count("d") == 1


def test_audit_serves_cheap_answer_but_records_teacher_label(tmp_path: Path) -> None:
    eng, store = make_engine(tmp_path, audit_rate=1.0, recal_every=10_000)
    d = eng.decide("x c=0.95")
    assert (d.label, d.path, d.audited) == ("s", "cheap", True)
    assert eng.flush_audits()
    conf, err = store.recent("d", 5)
    assert conf.tolist() == [0.95] and err.tolist() == [1.0]  # student 's' != teacher 't'


def test_escalated_unaudited_items_are_not_stored_for_calibration(tmp_path: Path) -> None:
    eng, store = make_engine(tmp_path, audit_rate=0.0)
    eng.decide("x c=0.2")
    assert eng.flush_audits() and store.count("d") == 0


def test_teacher_failure_fail_open_serves_degraded(tmp_path: Path) -> None:
    eng, _ = make_engine(tmp_path, teacher=make_teacher(fail=True), fail_open=True)
    d = eng.decide("x c=0.2")
    assert (d.label, d.path) == ("s", "cheap_degraded")
    assert eng.stats.teacher_errors == 1


def test_teacher_failure_fail_closed_raises(tmp_path: Path) -> None:
    eng, _ = make_engine(tmp_path, teacher=make_teacher(fail=True), fail_open=False)
    with pytest.raises(TeacherUnavailableError):
        eng.decide("x c=0.2")


def test_audit_failure_on_cheap_path_still_answers(tmp_path: Path) -> None:
    eng, _ = make_engine(tmp_path, teacher=make_teacher(fail=True), audit_rate=1.0, fail_open=False)
    assert eng.decide("x c=0.95").path == "cheap"


def test_teacher_timeout_is_treated_as_failure(tmp_path: Path) -> None:
    eng, _ = make_engine(
        tmp_path, teacher=make_teacher(delay=0.5), teacher_timeout_s=0.05, fail_open=False
    )
    with pytest.raises(TeacherUnavailableError):
        eng.decide("x c=0.2")
    eng.close()


def test_recalibration_certifies_then_withdraws(tmp_path: Path) -> None:
    eng, _ = make_engine(
        tmp_path,
        threshold=None,
        teacher=make_teacher("s"),
        audit_rate=1.0,
        recal_every=60,
        min_labels=50,
        window_labels=200,
        alpha=0.1,
    )
    for _ in range(60):  # teacher agrees with student at high confidence
        eng.decide("x c=0.97")
    assert eng.flush_audits()
    assert eng.threshold is not None and eng.stats.recalibrations == 1
    # the teacher now disagrees: after the window turns over, nothing is certifiable
    eng2, _ = make_engine(
        tmp_path / "..",
        threshold=0.9,
        teacher=make_teacher("t"),
        audit_rate=1.0,
        recal_every=60,
        min_labels=50,
        window_labels=100,
        alpha=0.1,
    )
    for _ in range(60):
        eng2.decide("x c=0.97")
    assert eng2.flush_audits()
    assert eng2.threshold is None


def test_drift_alarm_when_accepted_items_start_failing(tmp_path: Path) -> None:
    eng, _ = make_engine(
        tmp_path,
        threshold=0.5,
        teacher=make_teacher("t"),
        audit_rate=1.0,
        recal_every=10_000,
        alpha=0.05,
    )
    for _ in range(200):
        eng.decide("x c=0.9")  # student 's' always disagrees with teacher 't'
    assert eng.flush_audits()
    assert eng.stats.drift_alarm and eng.stats.risk_lower > 0.05


# ---- regressions for the two measured defects ---------------------------------------------------


def test_audited_confident_request_does_not_wait_for_the_teacher(tmp_path: Path) -> None:
    eng, store = make_engine(
        tmp_path, teacher=make_teacher(delay=0.3), audit_rate=1.0, recal_every=10_000
    )
    started = time.perf_counter()
    d = eng.decide("x c=0.95")
    elapsed = time.perf_counter() - started
    assert (d.path, d.audited) == ("cheap", True)
    assert elapsed < 0.1  # before the fix this took about 0.3 s (the teacher's latency)
    assert eng.flush_audits(5.0) and store.count("d") == 1
    eng.close()


def test_audit_queue_full_drops_and_counts_without_blocking(tmp_path: Path) -> None:
    gate = threading.Event()
    eng, store = make_engine(
        tmp_path,
        teacher=make_teacher(gate=gate),
        audit_rate=1.0,
        recal_every=10_000,
        audit_workers=1,
        audit_queue_size=1,
    )
    started = time.perf_counter()
    for _ in range(6):
        eng.decide("x c=0.95")  # never blocks, even though the teacher is stuck
    assert time.perf_counter() - started < 0.5
    assert eng.stats.audits_dropped >= 3 and eng.audit_queue_depth <= 1
    gate.set()
    assert eng.flush_audits(5.0)
    assert store.count("d") + eng.stats.audits_dropped == 6  # nothing lost silently
    eng.close()


def test_failed_audit_write_does_not_fail_the_request(tmp_path: Path) -> None:
    eng, store = make_engine(tmp_path, audit_rate=1.0, recal_every=10_000)

    def boom(*_a: object, **_k: object) -> None:
        raise sqlite3.OperationalError("disk I/O error")

    store.add_audit = boom  # type: ignore[method-assign]
    d = eng.decide("x c=0.95")
    assert d.path == "cheap"  # before the fix: HTTP 500 on audited requests
    assert eng.flush_audits() and eng.stats.audit_errors == 1
    eng.close()


def test_teacher_recovers_without_waiting_for_stalled_calls(tmp_path: Path) -> None:
    delay = {"s": 3.0}

    def teacher(text: str) -> TeacherResponse:
        time.sleep(delay["s"])
        return TeacherResponse("t", "fake", 1, 1, 0.0, 1.0)

    eng, _ = make_engine(
        tmp_path,
        threshold=None,
        teacher=teacher,
        teacher_timeout_s=0.3,
        fail_open=False,
        teacher_workers=32,
    )
    errors: list[str] = []

    def call() -> None:
        try:
            eng.decide("x c=0.2")
        except TeacherUnavailableError:
            errors.append("timeout")

    ts = [threading.Thread(target=call) for _ in range(16)]  # more than the old pool of 8
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert len(errors) == 16
    delay["s"] = 0.0  # the teacher recovers while the stalled calls are still running
    started = time.perf_counter()
    assert eng.decide("x c=0.2").path == "teacher"  # before the fix: timed out for about 2.5 s
    assert time.perf_counter() - started < 0.5
    eng.close()


def test_saturated_teacher_slots_fail_fast_and_are_released(tmp_path: Path) -> None:
    gate = threading.Event()
    eng, _ = make_engine(
        tmp_path,
        threshold=None,
        teacher=make_teacher(gate=gate),
        teacher_timeout_s=0.2,
        fail_open=False,
        teacher_workers=2,
    )
    for _ in range(2):  # these two calls time out but keep their slots until the call ends
        with pytest.raises(TeacherUnavailableError):
            eng.decide("x c=0.2")
    started = time.perf_counter()
    with pytest.raises(TeacherUnavailableError, match="saturated"):
        eng.decide("x c=0.2")
    assert time.perf_counter() - started < 0.1  # fails at once instead of queueing and timing out
    assert eng.teacher_in_flight == 2
    gate.set()
    for _ in range(100):
        if eng.teacher_in_flight == 0:
            break
        time.sleep(0.02)
    assert eng.teacher_in_flight == 0
    assert eng.decide("x c=0.2").path == "teacher"  # slots came back
    eng.close()
