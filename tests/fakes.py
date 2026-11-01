"""Shared test doubles: a student whose confidence is encoded in the input text."""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from cascade.engine import Engine, EngineConfig
from cascade.store import AuditStore
from cascade.teacher import TeacherResponse

FloatArray = NDArray[np.float64]


def embed(text: str) -> FloatArray:
    m = re.search(r"c=([0-9.]+)", text)
    return np.array([float(m.group(1)) if m else 0.5, 0.0])


class FakeStudent:
    def predict_with_confidence(self, x: FloatArray) -> tuple[NDArray[np.str_], FloatArray]:
        return np.array(["s"] * len(x)), x[:, 0].copy()


def make_teacher(
    label: str = "t",
    cost: float = 0.001,
    fail: bool = False,
    delay: float = 0.0,
    gate: threading.Event | None = None,
) -> Callable[[str], TeacherResponse]:
    def teacher(text: str) -> TeacherResponse:
        if gate is not None:
            gate.wait(5)
        if delay:
            time.sleep(delay)
        if fail:
            msg = "boom"
            raise RuntimeError(msg)
        return TeacherResponse(label, "fake", 10, 2, cost, 1.0)

    return teacher


def make_engine(
    tmp_path: Path,
    threshold: float | None = 0.8,
    teacher: Callable[[str], TeacherResponse] | None = None,
    **cfg: object,
) -> tuple[Engine, AuditStore]:
    store = AuditStore(tmp_path / "audit.db")
    base: dict[str, object] = {"decision": "d", "alpha": 0.1, "audit_rate": 0.0, "seed": 0}
    config = EngineConfig(**{**base, **cfg})  # type: ignore[arg-type]
    return Engine(config, embed, FakeStudent(), teacher or make_teacher(), store, threshold), store
