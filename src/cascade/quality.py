"""Data-quality checks for the audit store (run before trusting a recalibration or a report)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from cascade.store import AuditStore


@dataclass
class QualityReport:
    rows: int = 0
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def check_audit(
    store: AuditStore, decision: str, labels: set[str], min_rows: int = 100
) -> QualityReport:
    """Checks: enough rows, confidences in [0, 1], labels inside the closed set, no teacher
    refusals/invalid markers beyond 5%, no extreme duplicate share, and a stable disagreement rate
    between the older and newer half of the window (a large jump is flagged, not proven drift)."""
    rep = QualityReport()
    with store._lock:
        rows = store._conn.execute(
            "SELECT confidence, student_label, teacher_label, text_sha256 FROM audit "
            "WHERE decision = ? ORDER BY id",
            (decision,),
        ).fetchall()
    rep.rows = len(rows)
    if len(rows) < min_rows:
        rep.problems.append(f"only {len(rows)} audited rows (< {min_rows})")
        return rep
    conf = np.array([r[0] for r in rows], dtype=np.float64)
    if ((conf < 0) | (conf > 1) | np.isnan(conf)).any():
        rep.problems.append("confidence outside [0, 1] or NaN")
    bad_student = sum(r[1] not in labels for r in rows)
    if bad_student:
        rep.problems.append(f"{bad_student} student labels outside the label set")
    invalid = sum(r[2] == "__invalid__" for r in rows)
    foreign = sum(r[2] not in labels and r[2] != "__invalid__" for r in rows)
    if foreign:
        rep.problems.append(f"{foreign} teacher labels outside the label set")
    if invalid / len(rows) > 0.05:
        rep.problems.append(f"{invalid / len(rows):.1%} teacher answers invalid (> 5%)")
    dup = 1 - len({r[3] for r in rows}) / len(rows)
    if dup > 0.5:
        rep.problems.append(f"{dup:.0%} duplicate inputs: calibration is not independent")
    err = np.array([r[1] != r[2] for r in rows], dtype=np.float64)
    half = len(err) // 2
    older, newer = float(err[:half].mean()), float(err[half:].mean())
    if abs(newer - older) > 0.15:
        rep.problems.append(f"disagreement rate moved {older:.2f} -> {newer:.2f} within the window")
    return rep
