import math
from typing import Any

import pytest

from cascade.economics import (
    break_even_daily_volume,
    break_even_volume,
    cumulative_net,
    payback_days,
    savings_per_decision,
)


def test_closed_form_matches_cumulative_crossing() -> None:
    kw: dict[str, Any] = {
        "coverage": 0.5,
        "teacher_cost": 2e-4,
        "labels": 3000,
        "student_cost": 1e-6,
        "audit_rate": 0.05,
        "fixed_cost": 1.0,
    }
    v = break_even_volume(**kw)
    assert cumulative_net(v, **kw) == pytest.approx(0.0, abs=1e-9)
    assert cumulative_net(v * 0.9, **kw) < 0 < cumulative_net(v * 1.1, **kw)


def test_monotone_in_coverage_and_audit_rate() -> None:
    base: dict[str, Any] = {"teacher_cost": 1e-3, "labels": 1000}
    vols = [break_even_volume(coverage=c, **base) for c in (0.2, 0.4, 0.8)]
    assert vols[0] > vols[1] > vols[2]
    a = [break_even_volume(coverage=0.5, audit_rate=r, **base) for r in (0.0, 0.1, 0.5)]
    assert a[0] < a[1] < a[2]


def test_never_pays_back_when_savings_not_positive() -> None:
    assert math.isinf(break_even_volume(0.5, 1e-3, 100, student_cost=2e-3))
    assert math.isinf(break_even_volume(0.0, 1e-3, 100))
    assert math.isinf(break_even_volume(0.5, 1e-3, 100, audit_rate=1.0))


def test_zero_upfront_is_zero_and_validation() -> None:
    assert break_even_volume(0.5, 1e-3, 0) == 0.0
    with pytest.raises(ValueError, match="coverage"):
        savings_per_decision(1.5, 1e-3)
    with pytest.raises(ValueError, match="non-negative"):
        savings_per_decision(0.5, -1.0)


def test_daily_break_even_and_payback_are_consistent() -> None:
    kw: dict[str, Any] = {
        "coverage": 0.5,
        "teacher_cost": 2e-4,
        "student_cost": 8e-7,
        "audit_rate": 0.05,
        "hosting_per_day": 7.2,
    }
    v = break_even_daily_volume(**kw)
    assert v * savings_per_decision(0.5, 2e-4, 8e-7, 0.05) == pytest.approx(7.2)
    assert math.isinf(payback_days(v * 0.9, upfront=10_000, **kw))  # below break-even: never
    assert payback_days(v * 3, upfront=10_000, **kw) < payback_days(v * 2, upfront=10_000, **kw)
    assert math.isinf(break_even_daily_volume(0.5, 1e-3, student_cost=2e-3, hosting_per_day=1.0))
