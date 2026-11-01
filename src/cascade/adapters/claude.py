"""Claude teacher adapter for closed-set classification (structured JSON output).

Verified against the anthropic 2.3.0 SDK (2026-11-01): ``messages.create`` accepts ``thinking`` and
``output_config`` (``effort`` and ``format``, a JSON-schema output format). Haiku 5.5 rejects
non-default sampling parameters, so none are sent; determinism comes from the schema-constrained
output and a cache. Thinking is disabled (allowed at effort ``high`` or below on Haiku 5.5), so
output tokens are just the short JSON. Prices are passed in by the caller. The API key is read
from an environment variable and is never logged, cached or written to manifests. The SDK
performs its own retries (``max_retries``).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

from cascade.adapters.gemini import INVALID_LABEL, build_system_instruction, label_schema
from cascade.teacher import TeacherResponse


@dataclass(frozen=True)
class ClaudeConfig:
    model: str  # exact model id, recorded in every response
    labels: tuple[str, ...]
    instructions: str
    price_in_per_m: float  # USD per 1M input tokens
    price_out_per_m: float  # USD per 1M output tokens
    effort: str = "low"
    max_tokens: int = 64
    min_interval_s: float = 0.0
    max_retries: int = 2  # worst-case time per call is about timeout_s * (max_retries + 1)
    timeout_s: float = 10.0  # enforced by the HTTP client so a stalled call really ends
    api_key_env: str = "ANTHROPIC_API_KEY"


class ClaudeTeacher:
    """Callable teacher: ``text -> TeacherResponse`` (label, tokens, cost, latency)."""

    def __init__(self, cfg: ClaudeConfig, client: Any | None = None) -> None:
        self.cfg = cfg
        self._last_call = 0.0
        if client is None:
            if not os.environ.get(cfg.api_key_env):
                msg = f"environment variable {cfg.api_key_env} is not set"
                raise RuntimeError(msg)
            import anthropic  # noqa: PLC0415  (optional dependency)

            client = anthropic.Anthropic(max_retries=cfg.max_retries, timeout=cfg.timeout_s)
        self._client: Any = client

    def _schema(self) -> dict[str, Any]:
        schema = label_schema(self.cfg.labels)
        schema["additionalProperties"] = False
        return schema

    def __call__(self, text: str) -> TeacherResponse:
        gap = self.cfg.min_interval_s - (time.monotonic() - self._last_call)
        if gap > 0:
            time.sleep(gap)
        started = time.monotonic()
        try:
            response = self._client.messages.create(
                model=self.cfg.model,
                max_tokens=self.cfg.max_tokens,
                system=build_system_instruction(self._config_view()),
                messages=[{"role": "user", "content": text}],
                thinking={"type": "disabled"},
                output_config={
                    "effort": self.cfg.effort,
                    "format": {"type": "json_schema", "schema": self._schema()},
                },
            )
        finally:
            self._last_call = time.monotonic()
        return self._to_response(response, (self._last_call - started) * 1000.0)

    def _config_view(self) -> Any:
        # build_system_instruction only reads .instructions and .labels
        return self.cfg

    def _to_response(self, response: Any, latency_ms: float) -> TeacherResponse:
        label = INVALID_LABEL
        try:
            body = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
            candidate = str(json.loads(body).get("label"))
            if candidate in self.cfg.labels:
                label = candidate
        except (ValueError, TypeError, AttributeError):
            pass
        usage = response.usage
        in_tok = (
            int(getattr(usage, "input_tokens", 0) or 0)
            + int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
            + int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        )
        out_tok = int(getattr(usage, "output_tokens", 0) or 0)
        cost = (in_tok * self.cfg.price_in_per_m + out_tok * self.cfg.price_out_per_m) / 1e6
        return TeacherResponse(label, self.cfg.model, in_tok, out_tok, cost, latency_ms)
