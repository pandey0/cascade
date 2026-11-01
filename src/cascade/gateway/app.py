"""HTTP gateway: auth, validation, rate limiting, idempotency, backpressure, metrics.

Security defaults are fail-closed: without configured API keys every /v1 route returns 401
unless ``allow_anonymous`` is set explicitly (development only).
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import threading
import time
import uuid
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

from cascade.engine import Engine, TeacherUnavailableError
from cascade.store import AuditStore

log = logging.getLogger("cascade")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": round(record.created, 3),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    log.handlers[:] = [handler]
    log.setLevel(level)
    log.propagate = False


@dataclass(frozen=True)
class Settings:
    api_keys: tuple[str, ...] = ()  # plain keys get DEFAULT_SCOPES
    scoped_keys: tuple[tuple[str, frozenset[str]], ...] = ()
    auth_fail_per_min: int = 20  # failed-auth attempts per client address before lockout (429)
    hsts: bool = True
    allow_anonymous: bool = False
    rate_limit_per_min: int = 600
    max_input_chars: int = 4000
    max_concurrency: int = 32
    extra: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> Settings:
        plain: list[str] = []
        scoped: list[tuple[str, frozenset[str]]] = []
        for entry in (e.strip() for e in os.environ.get("CASCADE_API_KEYS", "").split(",")):
            if not entry:
                continue
            key, _, spec = entry.partition("@")  # "key" or "key@decide|status|admin"
            if not spec:
                plain.append(key)
                continue
            scopes = frozenset(spec.split("|"))
            bad = {x for x in scopes if x not in ("status", "admin") and not x.startswith("decide")}
            if bad:
                msg = f"unknown API key scopes: {sorted(bad)}"
                raise ValueError(msg)
            scoped.append((key, scopes))
        return cls(
            api_keys=tuple(plain),
            scoped_keys=tuple(scoped),
            auth_fail_per_min=int(os.environ.get("CASCADE_AUTH_FAIL_PER_MIN", "20")),
            allow_anonymous=os.environ.get("CASCADE_ALLOW_ANONYMOUS") == "1",
            rate_limit_per_min=int(os.environ.get("CASCADE_RATE_LIMIT_PER_MIN", "600")),
            max_input_chars=int(os.environ.get("CASCADE_MAX_INPUT_CHARS", "4000")),
            max_concurrency=int(os.environ.get("CASCADE_MAX_CONCURRENCY", "32")),
        )


DEFAULT_SCOPES = frozenset({"decide", "status"})


@dataclass(frozen=True)
class Principal:
    """An authenticated caller. Scopes: ``decide`` (any) or ``decide:<name>``, ``status``, ``admin``
    (admin implies everything, including recalibration)."""

    name: str
    scopes: frozenset[str]

    def can(self, scope: str, decision: str | None = None) -> bool:
        if "admin" in self.scopes or scope in self.scopes:
            return True
        return scope == "decide" and decision is not None and f"decide:{decision}" in self.scopes


class TokenBucket:
    """Per-client token bucket (in-memory: valid for a single replica; see docs/security.md)."""

    def __init__(self, per_minute: int) -> None:
        self.rate = per_minute / 60.0
        self.capacity = float(max(per_minute, 1))
        self._state: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def peek(self, client: str, now: float | None = None) -> bool:
        """True if a token is available, without consuming it."""
        t = time.monotonic() if now is None else now
        with self._lock:
            tokens, last = self._state.get(client, (self.capacity, t))
            return min(self.capacity, tokens + (t - last) * self.rate) >= 1.0

    def allow(self, client: str, now: float | None = None) -> bool:
        t = time.monotonic() if now is None else now
        with self._lock:
            tokens, last = self._state.get(client, (self.capacity, t))
            tokens = min(self.capacity, tokens + (t - last) * self.rate)
            if tokens < 1.0:
                self._state[client] = (tokens, t)
                return False
            self._state[client] = (tokens - 1.0, t)
            return True


class DecideRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=64)
    input: str = Field(min_length=1)


class DecideResponse(BaseModel):
    decision: str
    label: str
    path: str
    confidence: float
    request_id: str


def create_app(  # noqa: PLR0915
    engines: Mapping[str, Engine] | None = None,
    settings: Settings | None = None,
    store: AuditStore | None = None,
) -> FastAPI:
    cfg = settings or Settings()
    registry_engines = dict(engines or {})

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        for eng in registry_engines.values():  # drain pending audits, stop background workers
            eng.close()

    app = FastAPI(title="cascade gateway", version="0.1.0", lifespan=lifespan)
    reg = CollectorRegistry()
    decisions_total = Counter(
        "cascade_decisions_total", "Decisions served", ["decision", "path"], registry=reg
    )
    latency = Histogram(
        "cascade_decide_seconds",
        "Decide latency",
        ["decision"],
        registry=reg,
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
    )
    errors_total = Counter("cascade_errors_total", "Errors by kind", ["kind"], registry=reg)
    teacher_usd = Gauge(
        "cascade_teacher_spend_usd", "Cumulative teacher spend", ["decision"], registry=reg
    )
    audit_depth_g = Gauge(
        "cascade_audit_queue_depth",
        "Audits waiting for a background worker",
        ["decision"],
        registry=reg,
    )
    audit_dropped_g = Gauge(
        "cascade_audits_dropped",
        "Audits dropped because the queue was full (cumulative)",
        ["decision"],
        registry=reg,
    )
    in_flight_g = Gauge(
        "cascade_teacher_in_flight",
        "Request-path teacher calls in progress",
        ["decision"],
        registry=reg,
    )
    threshold_g = Gauge(
        "cascade_threshold", "Current confidence threshold (-1 = none)", ["decision"], registry=reg
    )
    risk_lower_g = Gauge(
        "cascade_risk_lower_bound",
        "Anytime-valid lower bound on audited risk",
        ["decision"],
        registry=reg,
    )
    drift_g = Gauge(
        "cascade_drift_alarm", "1 if the risk monitor is alarming", ["decision"], registry=reg
    )
    bucket = TokenBucket(cfg.rate_limit_per_min)
    gate = threading.BoundedSemaphore(cfg.max_concurrency)

    fail_bucket = TokenBucket(cfg.auth_fail_per_min)
    key_table: list[tuple[str, Principal]] = [
        (k, Principal(k[:4] + "…", DEFAULT_SCOPES)) for k in cfg.api_keys
    ] + [(k, Principal(k[:4] + "…", sc)) for k, sc in cfg.scoped_keys]

    def auth(request: Request, x_api_key: str | None = Header(default=None)) -> Principal:
        if cfg.allow_anonymous:
            return Principal("anonymous", frozenset({"admin"}))
        ip = request.client.host if request.client else "unknown"
        if not fail_bucket.peek(ip):  # brute-force lockout (ASVS V6.3.1)
            errors_total.labels("auth_lockout").inc()
            raise HTTPException(
                status_code=429, detail="too many failed attempts", headers={"Retry-After": "60"}
            )
        if x_api_key:
            found: Principal | None = None
            for k, principal in key_table:  # no early exit: constant work per key
                if hmac.compare_digest(x_api_key, k):
                    found = principal
            if found is not None:
                return found
        fail_bucket.allow(ip)  # consume a token on failure
        errors_total.labels("auth").inc()
        log.warning("auth_failed", extra={"fields": {"client": ip, "path": request.url.path}})
        raise HTTPException(status_code=401, detail="missing or invalid API key")

    def require(scope: str, decision: str | None, who: Principal) -> None:
        if not who.can(scope, decision):
            errors_total.labels("forbidden").inc()
            raise HTTPException(status_code=403, detail="insufficient scope")

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):  # type: ignore[no-untyped-def,unused-ignore]
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.rid = rid
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/v1"):
            response.headers["Cache-Control"] = "no-store"
        if cfg.hsts:  # effective only over TLS (terminated in front of the app); ASVS V3.4.1
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> JSONResponse:
        ok = bool(registry_engines) and (store is None or store.integrity_ok())
        return JSONResponse(
            {"ready": ok, "decisions": sorted(registry_engines)}, status_code=200 if ok else 503
        )

    @app.get("/metrics")
    def metrics() -> Response:
        for name, eng in registry_engines.items():
            teacher_usd.labels(name).set(eng.stats.spent_usd)
            threshold_g.labels(name).set(-1.0 if eng.threshold is None else eng.threshold)
            risk_lower_g.labels(name).set(max(0.0, eng.stats.risk_lower))
            drift_g.labels(name).set(float(eng.stats.drift_alarm))
            audit_depth_g.labels(name).set(eng.audit_queue_depth)
            audit_dropped_g.labels(name).set(eng.stats.audits_dropped)
            in_flight_g.labels(name).set(eng.teacher_in_flight)
        return Response(generate_latest(reg), media_type="text/plain; version=0.0.4")

    @app.post("/v1/decide", response_model=DecideResponse)
    def decide(
        req: DecideRequest,
        request: Request,
        response: Response,
        who: Principal = Depends(auth),  # noqa: B008
        idempotency_key: str | None = Header(default=None),
    ) -> DecideResponse | JSONResponse:
        rid = request.state.rid
        require("decide", req.decision, who)
        client = who.name
        if len(req.input) > cfg.max_input_chars:
            errors_total.labels("too_large").inc()
            raise HTTPException(
                status_code=413, detail=f"input exceeds {cfg.max_input_chars} characters"
            )
        if idempotency_key is not None and not 1 <= len(idempotency_key) <= 128:
            raise HTTPException(status_code=422, detail="Idempotency-Key must be 1-128 characters")
        engine = registry_engines.get(req.decision)
        if engine is None:
            raise HTTPException(status_code=404, detail="unknown decision")
        if store is not None and idempotency_key:
            cached = store.get_idempotent(f"{req.decision}:{idempotency_key}")
            if cached is not None:
                response.headers["Idempotent-Replay"] = "true"
                return DecideResponse.model_validate({**cached, "request_id": rid})
        if not bucket.allow(client):
            errors_total.labels("rate_limited").inc()
            raise HTTPException(
                status_code=429, detail="rate limit exceeded", headers={"Retry-After": "1"}
            )
        if not gate.acquire(blocking=False):
            errors_total.labels("overloaded").inc()
            raise HTTPException(status_code=503, detail="overloaded", headers={"Retry-After": "1"})
        started = time.perf_counter()
        try:
            d = engine.decide(req.input)
        except TeacherUnavailableError as exc:
            errors_total.labels("teacher_unavailable").inc()
            raise HTTPException(
                status_code=503, detail="teacher unavailable", headers={"Retry-After": "5"}
            ) from exc
        finally:
            gate.release()
        elapsed = time.perf_counter() - started
        latency.labels(req.decision).observe(elapsed)
        decisions_total.labels(req.decision, d.path).inc()
        log.info(
            "decide",
            extra={
                "fields": {
                    "rid": rid,
                    "decision": req.decision,
                    "path": d.path,
                    "ms": round(elapsed * 1000, 2),
                    "audited": d.audited,
                }
            },
        )
        out = DecideResponse(
            decision=req.decision,
            label=d.label,
            path=d.path,
            confidence=round(d.confidence, 6),
            request_id=rid,
        )
        if store is not None and idempotency_key:
            store.put_idempotent(f"{req.decision}:{idempotency_key}", out.model_dump())
        return out

    @app.get("/v1/status/{decision}")
    def status(
        decision: str,
        who: Principal = Depends(auth),  # noqa: B008
    ) -> dict[str, object]:
        require("status", None, who)
        eng = registry_engines.get(decision)
        if eng is None:
            raise HTTPException(status_code=404, detail="unknown decision")
        s = eng.stats
        return {
            "decision": decision,
            "threshold": eng.threshold,
            "decisions": s.decisions,
            "audits": s.audits,
            "teacher_calls": s.teacher_calls,
            "teacher_errors": s.teacher_errors,
            "spent_usd": s.spent_usd,
            "recalibrations": s.recalibrations,
            "drift_alarm": s.drift_alarm,
            "risk_lower_bound": s.risk_lower,
            "audit_queue_depth": eng.audit_queue_depth,
            "audits_dropped": s.audits_dropped,
            "audit_errors": s.audit_errors,
            "teacher_in_flight": eng.teacher_in_flight,
            "shadow": eng.cfg.shadow,
            "alpha": eng.cfg.alpha,
        }

    @app.post("/v1/recalibrate/{decision}")
    def recalibrate(
        decision: str,
        who: Principal = Depends(auth),  # noqa: B008
    ) -> dict[str, object]:
        require("admin", None, who)
        eng = registry_engines.get(decision)
        if eng is None:
            raise HTTPException(status_code=404, detail="unknown decision")
        return {"decision": decision, "threshold": eng.recalibrate()}

    return app
