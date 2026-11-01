"""Measure the two engine defects found in the critique, on whatever `cascade` is importable.

(1) Tail latency of confident requests when 5% are audited and the teacher takes 300 ms.
(2) Recovery after a stalled teacher: 16 concurrent calls stall (3 s each, request timeout 0.5 s),
    then the teacher recovers; how long until a request succeeds again?

Run it against two checkouts (set PYTHONPATH to that checkout's src) to compare before and after:
    PYTHONPATH=<checkout>/src python scripts/measure_defects.py > before.json
Uses only the public decide() API so it works on the old engine too. Prints JSON.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # for tests.fakes (embed, FakeStudent)

from tests.fakes import FakeStudent, embed  # noqa: E402

from cascade.engine import Engine, EngineConfig, TeacherUnavailableError  # noqa: E402
from cascade.store import AuditStore  # noqa: E402
from cascade.teacher import TeacherResponse  # noqa: E402


def make(tmp: Path, name: str, teacher, **cfg):  # type: ignore[no-untyped-def]
    fields = {f.name for f in dataclasses.fields(EngineConfig)}
    kw = {
        k: v
        for k, v in {"decision": "d", "alpha": 0.1, "seed": 1, "recal_every": 10**9, **cfg}.items()
        if k in fields
    }
    thr = cfg.get("threshold")
    return Engine(EngineConfig(**kw), embed, FakeStudent(), teacher, AuditStore(tmp / name), thr)


def tail_latency(tmp: Path) -> dict[str, float]:
    def teacher(_t: str) -> TeacherResponse:
        time.sleep(0.3)
        return TeacherResponse("t", "fake", 1, 1, 0.0, 300.0)

    eng = make(tmp, "a.db", teacher, audit_rate=0.05, threshold=0.1)
    lat = []
    for _ in range(400):
        t0 = time.perf_counter()
        eng.decide("x c=0.95")
        lat.append((time.perf_counter() - t0) * 1000)
    arr = np.array(lat)
    if hasattr(eng, "close"):
        eng.close()
    return {
        "p50_ms": float(np.percentile(arr, 50)),
        "p95_ms": float(np.percentile(arr, 95)),
        "p99_ms": float(np.percentile(arr, 99)),
        "max_ms": float(arr.max()),
    }


def recovery(tmp: Path) -> dict[str, float]:
    delay = {"s": 3.0}

    def teacher(_t: str) -> TeacherResponse:
        time.sleep(delay["s"])
        return TeacherResponse("t", "fake", 1, 1, 0.0, 1.0)

    eng = make(
        tmp, "b.db", teacher, audit_rate=0.0, teacher_timeout_s=0.5, fail_open=False, threshold=None
    )
    stalled = []

    def call() -> None:
        try:
            eng.decide("x c=0.2")
            stalled.append("ok")
        except TeacherUnavailableError:
            stalled.append("timeout")

    ts = [threading.Thread(target=call) for _ in range(16)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    delay["s"] = 0.0  # recovered
    t0 = time.perf_counter()
    first_ok = None
    while time.perf_counter() - t0 < 10:
        try:
            eng.decide("x c=0.2")
            first_ok = time.perf_counter() - t0
            break
        except TeacherUnavailableError:
            time.sleep(0.05)
    if hasattr(eng, "close"):
        eng.close()
    return {
        "stalled_requests_all_timed_out": float(stalled.count("timeout") == 16),
        "seconds_until_first_success_after_recovery": float(
            first_ok if first_ok is not None else -1
        ),
    }


if __name__ == "__main__":
    import cascade

    tmp = Path(tempfile.mkdtemp())
    print(
        json.dumps(
            {
                "cascade_from": str(Path(cascade.__file__).parent),
                "tail_latency_confident_requests_5pct_audited": tail_latency(tmp),
                "recovery_after_stalled_teacher": recovery(tmp),
            },
            indent=2,
        )
    )
