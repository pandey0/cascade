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
from collections.abc import Mapping
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
    api_keys: tuple[str, ...] = ()
    allow_anonymous: bool = False
    rate_limit_per_min: int = 600
    max_input_chars: int = 4000
    max_concurrency: int = 32
    extra: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> Settings:
        keys = tuple(
            k.strip() for k in os.environ.get("CASCADE_API_KEYS", "").split(",") if k.strip()
        )
        return cls(
            api_keys=keys,
            allow_anonymous=os.environ.get("CASCADE_ALLOW_ANONYMOUS") == "1",
            rate_limit_per_min=int(os.environ.get("CASCADE_RATE_LIMIT_PER_MIN", "600")),
            max_input_chars=int(os.environ.get("CASCADE_MAX_INPUT_CHARS", "4000")),
            max_concurrency=int(os.environ.get("CASCADE_MAX_CONCURRENCY", "32")),
        )


class TokenBucket:
    """Per-client token bucket (in-memory: valid for a single replica; see docs/security.md)."""

    def __init__(self, per_minute: int) -> None:
        self.rate = per_minute / 60.0
        self.capacity = float(max(per_minute, 1))
        self._state: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

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
    app = FastAPI(title="cascade gateway", version="0.1.0")
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

    def auth(x_api_key: str | None = Header(default=None)) -> str:
        if cfg.allow_anonymous:
            return "anonymous"
        if x_api_key and any(hmac.compare_digest(x_api_key, k) for k in cfg.api_keys):
            return x_api_key[:4] + "…"
        errors_total.labels("auth").inc()
        raise HTTPException(status_code=401, detail="missing or invalid API key")

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):  # type: ignore[no-untyped-def,unused-ignore]
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.rid = rid
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = rid
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
        return Response(generate_latest(reg), media_type="text/plain; version=0.0.4")

    @app.post("/v1/decide", response_model=DecideResponse)
    def decide(
        req: DecideRequest,
        request: Request,
        response: Response,
        client: str = Depends(auth),
        idempotency_key: str | None = Header(default=None),
    ) -> DecideResponse | JSONResponse:
        rid = request.state.rid
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
    def status(decision: str, _client: str = Depends(auth)) -> dict[str, object]:
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
            "shadow": eng.cfg.shadow,
            "alpha": eng.cfg.alpha,
        }

    @app.post("/v1/recalibrate/{decision}")
    def recalibrate(decision: str, _client: str = Depends(auth)) -> dict[str, object]:
        eng = registry_engines.get(decision)
        if eng is None:
            raise HTTPException(status_code=404, detail="unknown decision")
        return {"decision": decision, "threshold": eng.recalibrate()}

    return app
