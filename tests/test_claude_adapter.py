import json
from types import SimpleNamespace

import pytest

from cascade.adapters.claude import ClaudeConfig, ClaudeTeacher
from cascade.adapters.gemini import INVALID_LABEL

LABELS = ("card_arrival", "refund_status", "lost_card")


def _cfg() -> ClaudeConfig:
    return ClaudeConfig("test-model", LABELS, "Classify.", price_in_per_m=0.1, price_out_per_m=0.5)


def _resp(text: str, i: int = 200, o: int = 8) -> SimpleNamespace:
    usage = SimpleNamespace(
        input_tokens=i, output_tokens=o, cache_creation_input_tokens=0, cache_read_input_tokens=0
    )
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], usage=usage)


class FakeClient:
    def __init__(self, responses: list[object]) -> None:
        self.calls: list[dict[str, object]] = []
        self._responses = list(responses)
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self._responses.pop(0)


def test_label_cost_and_request_shape() -> None:
    client = FakeClient([_resp(json.dumps({"label": "lost_card"}))])
    out = ClaudeTeacher(_cfg(), client)("I lost my card")
    assert out.label == "lost_card" and out.model == "test-model"
    assert out.input_tokens == 200 and out.output_tokens == 8
    assert out.cost_usd == pytest.approx((200 * 0.1 + 8 * 0.5) / 1e6)
    sent = client.calls[0]
    assert sent["thinking"] == {"type": "disabled"}
    assert "temperature" not in sent  # Haiku 5.5 rejects non-default sampling
    fmt = sent["output_config"]["format"]  # type: ignore[index]
    assert fmt["schema"]["additionalProperties"] is False
    assert fmt["schema"]["properties"]["label"]["enum"] == list(LABELS)


def test_invalid_outputs_marked() -> None:
    client = FakeClient([_resp('{"label": "pause_music"}'), _resp("nope")])
    teacher = ClaudeTeacher(_cfg(), client)
    assert teacher("a").label == INVALID_LABEL
    assert teacher("b").label == INVALID_LABEL


def test_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY is not set"):
        ClaudeTeacher(_cfg())
