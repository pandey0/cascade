import threading
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from cascade.gateway.app import Settings, TokenBucket, create_app

from .fakes import make_engine, make_teacher

KEY = {"X-API-Key": "k-test"}


def _client(tmp_path: Path, settings: Settings | None = None, **kw: Any) -> TestClient:
    eng, store = make_engine(tmp_path, **kw)
    s = settings or Settings(api_keys=("k-test",))
    return TestClient(create_app({"d": eng}, s, store))


def test_health_ready_and_request_id(tmp_path: Path) -> None:
    c = _client(tmp_path)
    r = c.get("/healthz", headers={"X-Request-ID": "abc"})
    assert r.json() == {"status": "ok"} and r.headers["X-Request-ID"] == "abc"
    assert c.get("/readyz").json()["ready"] is True
    empty = TestClient(create_app())
    assert empty.get("/readyz").status_code == 503


def test_fail_closed_without_keys_and_wrong_key(tmp_path: Path) -> None:
    body = {"decision": "d", "input": "x c=0.9"}
    c = _client(tmp_path, Settings())
    assert c.post("/v1/decide", json=body).status_code == 401
    c2 = _client(tmp_path / "2" if False else tmp_path)
    assert c2.post("/v1/decide", json=body, headers={"X-API-Key": "nope"}).status_code == 401
    assert c2.post("/v1/decide", json=body, headers=KEY).status_code == 200


def test_anonymous_only_when_explicit(tmp_path: Path) -> None:
    c = _client(tmp_path, Settings(allow_anonymous=True))
    assert c.post("/v1/decide", json={"decision": "d", "input": "x c=0.9"}).status_code == 200


def test_validation_and_limits(tmp_path: Path) -> None:
    c = _client(tmp_path, Settings(api_keys=("k-test",), max_input_chars=20))
    assert c.post("/v1/decide", json={"decision": "d"}, headers=KEY).status_code == 422
    assert c.post("/v1/decide", json={"decision": "d", "input": ""}, headers=KEY).status_code == 422
    big = {"decision": "d", "input": "z" * 21}
    assert c.post("/v1/decide", json=big, headers=KEY).status_code == 413
    assert (
        c.post("/v1/decide", json={"decision": "q", "input": "a"}, headers=KEY).status_code == 404
    )
    bad = {**KEY, "Idempotency-Key": "k" * 200}
    assert (
        c.post("/v1/decide", json={"decision": "d", "input": "a"}, headers=bad).status_code == 422
    )


def test_idempotency_replays_without_second_teacher_call(tmp_path: Path) -> None:
    calls = []
    inner = make_teacher("t")

    def spy(text: str):  # type: ignore[no-untyped-def]
        calls.append(text)
        return inner(text)

    c = _client(tmp_path, teacher=spy)
    body = {"decision": "d", "input": "x c=0.1"}
    h = {**KEY, "Idempotency-Key": "abc"}
    first = c.post("/v1/decide", json=body, headers=h)
    second = c.post("/v1/decide", json=body, headers=h)
    assert first.json()["label"] == second.json()["label"] == "t" and len(calls) == 1
    assert (
        second.headers["Idempotent-Replay"] == "true" and "Idempotent-Replay" not in first.headers
    )


def test_rate_limit_returns_429(tmp_path: Path) -> None:
    c = _client(tmp_path, Settings(api_keys=("k-test",), rate_limit_per_min=2))
    codes = [
        c.post("/v1/decide", json={"decision": "d", "input": "x c=0.9"}, headers=KEY).status_code
        for _ in range(5)
    ]
    assert codes[:2] == [200, 200] and 429 in codes[2:]


def test_token_bucket_refills() -> None:
    b = TokenBucket(60)  # 1/s, capacity 60
    assert all(b.allow("a", now=0.0) for _ in range(60)) and not b.allow("a", now=0.0)
    assert b.allow("a", now=2.0)


def test_teacher_unavailable_maps_to_503(tmp_path: Path) -> None:
    c = _client(tmp_path, teacher=make_teacher(fail=True), fail_open=False)
    r = c.post("/v1/decide", json={"decision": "d", "input": "x c=0.1"}, headers=KEY)
    assert r.status_code == 503 and r.headers["Retry-After"] == "5"


def test_backpressure_when_saturated(tmp_path: Path) -> None:
    gate = threading.Event()
    c = _client(
        tmp_path, Settings(api_keys=("k-test",), max_concurrency=1), teacher=make_teacher(gate=gate)
    )
    body = {"decision": "d", "input": "x c=0.1"}
    first: list[int] = []
    t = threading.Thread(
        target=lambda: first.append(c.post("/v1/decide", json=body, headers=KEY).status_code)
    )
    t.start()
    for _ in range(100):  # wait until the first request holds the slot
        if c.get("/v1/status/d", headers=KEY).json()["teacher_calls"] >= 1:
            break
        threading.Event().wait(0.02)
    assert c.post("/v1/decide", json=body, headers=KEY).status_code == 503
    gate.set()
    t.join(5)
    assert first == [200]


def test_metrics_and_status(tmp_path: Path) -> None:
    c = _client(tmp_path)
    c.post("/v1/decide", json={"decision": "d", "input": "x c=0.9"}, headers=KEY)
    text = c.get("/metrics").text
    assert 'cascade_decisions_total{decision="d",path="cheap"} 1.0' in text
    assert "cascade_decide_seconds_bucket" in text and "cascade_threshold" in text
    st = c.get("/v1/status/d", headers=KEY).json()
    assert st["decisions"] == 1 and st["threshold"] == 0.8
    assert c.get("/v1/status/d").status_code == 401
    assert c.post("/v1/recalibrate/d", headers=KEY).status_code == 200
    assert c.get("/v1/status/zzz", headers=KEY).status_code == 404
