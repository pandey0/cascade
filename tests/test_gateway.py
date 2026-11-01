import threading
from pathlib import Path
from typing import Any

import pytest
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
    assert c.post("/v1/recalibrate/d", headers=KEY).status_code == 403  # plain keys lack admin
    assert c.get("/v1/status/zzz", headers=KEY).status_code == 404


ADMIN = {"X-API-Key": "k-admin"}
BODY = {"decision": "d", "input": "x c=0.9"}


def test_scopes_and_admin_only_recalibration(tmp_path: Path) -> None:
    s = Settings(
        api_keys=("k-test",),
        scoped_keys=(
            ("k-admin", frozenset({"admin"})),
            ("k-ro", frozenset({"status"})),
            ("k-one", frozenset({"decide:other"})),
        ),
    )
    c = _client(tmp_path, s)
    assert c.post("/v1/recalibrate/d", headers=ADMIN).status_code == 200
    assert c.post("/v1/decide", json=BODY, headers=ADMIN).status_code == 200  # admin implies all
    ro = {"X-API-Key": "k-ro"}
    assert c.get("/v1/status/d", headers=ro).status_code == 200
    assert c.post("/v1/decide", json=BODY, headers=ro).status_code == 403
    one = {"X-API-Key": "k-one"}
    assert c.post("/v1/decide", json=BODY, headers=one).status_code == 403  # wrong decision
    assert c.get("/v1/status/d", headers=one).status_code == 403


def test_settings_parse_scoped_keys_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CASCADE_API_KEYS", "plain1, k2@status|decide:d ,k3@admin")
    s = Settings.from_env()
    assert s.api_keys == ("plain1",)
    assert dict(s.scoped_keys) == {
        "k2": frozenset({"status", "decide:d"}),
        "k3": frozenset({"admin"}),
    }
    monkeypatch.setenv("CASCADE_API_KEYS", "k@bogus")
    with pytest.raises(ValueError, match="unknown API key scopes"):
        Settings.from_env()


def test_failed_auth_lockout_and_valid_key_still_works_for_others(tmp_path: Path) -> None:
    c = _client(tmp_path, Settings(api_keys=("k-test",), auth_fail_per_min=3))
    bad = {"X-API-Key": "wrong"}
    codes = [c.post("/v1/decide", json=BODY, headers=bad).status_code for _ in range(6)]
    assert codes[:3] == [401, 401, 401] and 429 in codes[3:]
    # the locked-out client address is refused even with a valid key (brute-force control)
    assert c.post("/v1/decide", json=BODY, headers=KEY).status_code == 429


def test_security_headers(tmp_path: Path) -> None:
    c = _client(tmp_path)
    r = c.post("/v1/decide", json=BODY, headers=KEY)
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Cache-Control"] == "no-store"
    assert "max-age=31536000" in r.headers["Strict-Transport-Security"]
    assert "Cache-Control" not in c.get("/healthz").headers
    off = _client(tmp_path / "x" if False else tmp_path, Settings(api_keys=("k-test",), hsts=False))
    assert "Strict-Transport-Security" not in off.get("/healthz").headers


def test_no_cors_headers_by_default(tmp_path: Path) -> None:
    c = _client(tmp_path)
    r = c.get("/healthz", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}
