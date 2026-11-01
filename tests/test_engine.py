from pathlib import Path

import pytest

from cascade.engine import TeacherUnavailableError

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
    assert store.count("d") == 1


def test_audit_serves_cheap_answer_but_records_teacher_label(tmp_path: Path) -> None:
    eng, store = make_engine(tmp_path, audit_rate=1.0, recal_every=10_000)
    d = eng.decide("x c=0.95")
    assert (d.label, d.path, d.audited) == ("s", "cheap", True)
    conf, err = store.recent("d", 5)
    assert conf.tolist() == [0.95] and err.tolist() == [1.0]  # student 's' != teacher 't'


def test_escalated_unaudited_items_are_not_stored_for_calibration(tmp_path: Path) -> None:
    eng, store = make_engine(tmp_path, audit_rate=0.0)
    eng.decide("x c=0.2")
    assert store.count("d") == 0


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
    assert eng.stats.drift_alarm and eng.stats.risk_lower > 0.05
