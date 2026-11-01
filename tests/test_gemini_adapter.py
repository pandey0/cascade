import json
from types import SimpleNamespace

import pytest
from google import genai

from cascade.adapters.gemini import (
    INVALID_LABEL,
    GeminiConfig,
    GeminiTeacher,
    build_system_instruction,
    label_schema,
)

pytest.importorskip("google.genai")

LABELS = ("card_arrival", "refund_status", "lost_card")


def _cfg(**kw: object) -> GeminiConfig:
    base = {
        "model": "test-model",
        "labels": LABELS,
        "instructions": "Classify the message.",
        "price_in_per_m": 1.0,
        "price_out_per_m": 4.0,
        "backoff_base_s": 0.0,
    }
    return GeminiConfig(**{**base, **kw})  # type: ignore[arg-type]


def _response(text: str, p: int = 100, c: int = 10, t: int = 5) -> SimpleNamespace:
    usage = SimpleNamespace(prompt_token_count=p, candidates_token_count=c, thoughts_token_count=t)
    return SimpleNamespace(text=text, usage_metadata=usage)


class FakeClient:
    def __init__(self, responses: list[object]) -> None:
        self.calls: list[dict[str, object]] = []
        self._responses = list(responses)
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class TransientError(Exception):
    code = 429


def test_label_cost_and_tokens() -> None:
    client = FakeClient([_response(json.dumps({"label": "lost_card"}))])
    out = GeminiTeacher(_cfg(), client)("I lost my card")
    assert out.label == "lost_card" and out.model == "test-model"
    assert out.input_tokens == 100 and out.output_tokens == 15  # thinking counted as output
    assert out.cost_usd == pytest.approx((100 * 1.0 + 15 * 4.0) / 1e6)
    sent = client.calls[0]
    assert sent["model"] == "test-model" and sent["contents"] == "I lost my card"


def test_out_of_set_and_malformed_outputs_are_marked_invalid() -> None:
    client = FakeClient([_response('{"label": "pause_music"}'), _response("not json")])
    teacher = GeminiTeacher(_cfg(), client)
    assert teacher("a").label == INVALID_LABEL
    assert teacher("b").label == INVALID_LABEL


def test_retries_transient_errors_then_succeeds_and_raises_on_permanent() -> None:
    ok = _response('{"label": "card_arrival"}')
    teacher = GeminiTeacher(_cfg(), FakeClient([TransientError(), TransientError(), ok]))
    assert teacher("x").label == "card_arrival"
    with pytest.raises(ValueError, match="bad request"):
        GeminiTeacher(_cfg(), FakeClient([ValueError("bad request")]))("x")
    with pytest.raises(TransientError):
        GeminiTeacher(_cfg(max_retries=1), FakeClient([TransientError(), TransientError()]))("x")


def test_missing_key_raises_without_leaking(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not set"):
        GeminiTeacher(_cfg())


def test_prompt_and_schema_helpers() -> None:
    cfg = _cfg()
    assert "card_arrival, refund_status, lost_card" in build_system_instruction(cfg)
    assert label_schema(LABELS)["properties"]["label"]["enum"] == list(LABELS)


def test_timeout_is_passed_to_the_http_client_in_milliseconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            seen.update(kwargs)

    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(genai, "Client", FakeClient)
    GeminiTeacher(_cfg(timeout_s=2.5))
    assert seen["http_options"].timeout == 2500  # type: ignore[attr-defined]
