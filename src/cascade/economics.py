"""Break-even economics of a cascade (RQ5). All money in the same unit (e.g. USD).

Model (stated assumptions, not measurements):
  * every escalated decision costs ``teacher_cost``; every student answer costs ``student_cost``;
  * a fraction ``audit_rate`` of *student-answered* decisions is additionally sent to the teacher
    so risk can be monitored (audited items that would be escalated anyway cost nothing extra);
  * one-off cost = ``labels`` teacher calls (training + initial calibration) + ``fixed_cost``;
  * coverage and risk are taken from the experiments and assumed constant (no drift costs).
Engineering time, infrastructure and the cost of student errors are NOT included.
"""

from __future__ import annotations

import math


def savings_per_decision(
    coverage: float, teacher_cost: float, student_cost: float = 0.0, audit_rate: float = 0.0
) -> float:
    """Expected saving per decision versus always calling the teacher."""
    if not (0.0 <= coverage <= 1.0 and 0.0 <= audit_rate <= 1.0):
        msg = "coverage and audit_rate must be in [0, 1]"
        raise ValueError(msg)
    if teacher_cost < 0 or student_cost < 0:
        msg = "costs must be non-negative"
        raise ValueError(msg)
    return coverage * (teacher_cost * (1.0 - audit_rate) - student_cost)


def break_even_volume(  # noqa: PLR0917
    coverage: float,
    teacher_cost: float,
    labels: int,
    student_cost: float = 0.0,
    audit_rate: float = 0.0,
    fixed_cost: float = 0.0,
) -> float:
    """Number of decisions after which cumulative savings cover the one-off cost (inf if never)."""
    gain = savings_per_decision(coverage, teacher_cost, student_cost, audit_rate)
    upfront = labels * teacher_cost + fixed_cost
    if upfront <= 0:
        return 0.0
    return math.inf if gain <= 0 else upfront / gain


def cumulative_net(  # noqa: PLR0917
    volume: float,
    coverage: float,
    teacher_cost: float,
    labels: int,
    student_cost: float = 0.0,
    audit_rate: float = 0.0,
    fixed_cost: float = 0.0,
) -> float:
    """Cumulative saving after ``volume`` decisions, net of the one-off cost."""
    gain = savings_per_decision(coverage, teacher_cost, student_cost, audit_rate)
    return volume * gain - (labels * teacher_cost + fixed_cost)
