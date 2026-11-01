"""Gemini teacher adapter for closed-set classification (structured JSON output).

Verified against google-genai 2.33.0 type definitions (2026-11-01): ``GenerateContentConfig`` has
``response_json_schema``, ``response_mime_type``, ``thinking_config``; ``ThinkingConfig`` has
``thinking_level`` (MINIMAL/LOW/MEDIUM/HIGH); usage metadata has ``prompt_token_count``,
``candidates_token_count`` and ``thoughts_token_count``. Thinking tokens are billed as output,
so they are counted in the cost. Prices are passed in by the caller (read from the provider's
pricing page at run time), never hard-coded. The API key is read from an environment variable and
is never logged, cached or written to manifests.
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass
from typing import Any

from cascade.teacher import TeacherResponse

INVALID_LABEL = "__invalid__"
TRANSIENT_CODES = frozenset({408, 429, 500, 502, 503, 504})


@dataclass(frozen=True)
class GeminiConfig:
    model: str  # exact model id; recorded in every response (ids change over time)
    labels: tuple[str, ...]
    instructions: str
    price_in_per_m: float  # USD per 1M input tokens
    price_out_per_m: float  # USD per 1M output tokens (thinking tokens count as output)
    thinking_level: str = "MINIMAL"
    max_output_tokens: int = 64
    temperature: float = 0.0
    seed: int | None = 0
    min_interval_s: float = 0.0  # spacing between calls, to respect rate limits
    max_retries: int = 5
    backoff_base_s: float = 1.0
    api_key_env: str = "GEMINI_API_KEY"


def build_system_instruction(cfg: GeminiConfig) -> str:
    return (
        f'{cfg.instructions}\nReturn JSON {{"label": <one of the labels>}}.\n'
        "Labels: " + ", ".join(cfg.labels)
    )


def label_schema(labels: tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"label": {"type": "string", "enum": list(labels)}},
        "required": ["label"],
    }


def _is_transient(exc: Exception) -> bool:
    code = getattr(exc, "code", None)
    return isinstance(code, int) and code in TRANSIENT_CODES


class GeminiTeacher:
    """Callable teacher: ``text -> TeacherResponse`` (label, tokens, cost, latency)."""

    def __init__(self, cfg: GeminiConfig, client: Any | None = None) -> None:
        self.cfg = cfg
        self._last_call = 0.0
        if client is None:
            key = os.environ.get(cfg.api_key_env)
            if not key:
                msg = f"environment variable {cfg.api_key_env} is not set"
                raise RuntimeError(msg)
            from google import genai  # noqa: PLC0415  (optional dependency)

            client = genai.Client(api_key=key)
        self._client = client

    def _config(self) -> Any:
        from google.genai import types  # noqa: PLC0415  (optional dependency)

        return types.GenerateContentConfig(
            system_instruction=build_system_instruction(self.cfg),
            response_mime_type="application/json",
            response_json_schema=label_schema(self.cfg.labels),
            temperature=self.cfg.temperature,
            seed=self.cfg.seed,
            max_output_tokens=self.cfg.max_output_tokens,
            thinking_config=types.ThinkingConfig(thinking_level=self.cfg.thinking_level),
        )

    def _wait(self) -> None:
        gap = self.cfg.min_interval_s - (time.monotonic() - self._last_call)
        if gap > 0:
            time.sleep(gap)

    def __call__(self, text: str) -> TeacherResponse:
        config = self._config()
        for attempt in range(self.cfg.max_retries + 1):
            self._wait()
            started = time.monotonic()
            try:
                response = self._client.models.generate_content(
                    model=self.cfg.model, contents=text, config=config
                )
            except Exception as exc:
                self._last_call = time.monotonic()
                if attempt >= self.cfg.max_retries or not _is_transient(exc):
                    raise
                delay = self.cfg.backoff_base_s * (2**attempt) * (0.5 + random.random())  # noqa: S311
                time.sleep(min(delay, 60.0))
                continue
            self._last_call = time.monotonic()
            return self._to_response(response, (self._last_call - started) * 1000.0)
        msg = "unreachable"
        raise RuntimeError(msg)

    def _to_response(self, response: Any, latency_ms: float) -> TeacherResponse:
        label = INVALID_LABEL
        try:
            parsed = json.loads(response.text)
            candidate = str(parsed.get("label"))
            if candidate in self.cfg.labels:
                label = candidate
        except (ValueError, TypeError, AttributeError):
            pass
        usage = getattr(response, "usage_metadata", None)
        in_tok = int(getattr(usage, "prompt_token_count", 0) or 0)
        out_tok = int(getattr(usage, "candidates_token_count", 0) or 0) + int(
            getattr(usage, "thoughts_token_count", 0) or 0
        )
        cost = (in_tok * self.cfg.price_in_per_m + out_tok * self.cfg.price_out_per_m) / 1e6
        return TeacherResponse(label, self.cfg.model, in_tok, out_tok, cost, latency_ms)
