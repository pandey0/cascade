from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from cascade.backends import JevBackend
from cascade.data import three_way_split
from cascade.spec import load_spec
from cascade.students import LogisticStudent
from cascade.teacher import BudgetExceededError, CachedTeacher, TeacherResponse

SPEC = """
name: ticket_urgency
labels: [low, normal, urgent]
teacher: {provider: example, model: example-model-id}
target: {agreement: 0.95, delta: 0.1}
examples:
  - {input: "site is down", label: urgent}
"""


def test_spec_loads_and_derives_alpha(tmp_path: Path) -> None:
    p = tmp_path / "s.yaml"
    p.write_text(SPEC)
    spec = load_spec(p)
    assert spec.risk_alpha == pytest.approx(0.05)
    assert spec.shadow_mode is True


def test_spec_rejects_bad_labels(tmp_path: Path) -> None:
    p = tmp_path / "s.yaml"
    p.write_text(SPEC.replace("[low, normal, urgent]", "[low, low]"))
    with pytest.raises(ValidationError):
        load_spec(p)
    p.write_text(SPEC.replace("label: urgent", "label: nope"))
    with pytest.raises(ValidationError):
        load_spec(p)


def _fake(cost: float = 0.01) -> tuple[Callable[[str], TeacherResponse], dict[str, int]]:
    calls = {"n": 0}

    def inner(text: str) -> TeacherResponse:
        calls["n"] += 1
        return TeacherResponse("a", "m", 10, 2, cost, 1.0)

    return inner, calls


def test_cached_teacher_caches_and_caps(tmp_path: Path) -> None:
    inner, calls = _fake()
    t = CachedTeacher(inner, tmp_path / "c.sqlite", "m", max_usd=0.015)
    t("x")
    t("x")  # cache hit
    assert calls["n"] == 1 and t.hits == 1 and t.misses == 1
    t("y")  # spend 0.02 >= cap now
    with pytest.raises(BudgetExceededError):
        t("z")
    t.close()


def test_split_keeps_duplicates_together() -> None:
    texts = [f"t{i % 40}" for i in range(400)]  # each text appears 10 times
    tr, ca, te = three_way_split(texts, seed=1)
    sets = [{texts[i] for i in part} for part in (tr, ca, te)]
    assert not (sets[0] & sets[1]) and not (sets[0] & sets[2]) and not (sets[1] & sets[2])
    assert len(tr) + len(ca) + len(te) == 400


def test_student_temperature_scaling_reduces_overconfidence() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(600, 5))
    y = np.where(x[:, 0] + 0.8 * rng.normal(size=600) > 0, "a", "b")
    s = LogisticStudent(c=1e3).fit(x[:300], y[:300])
    _, conf_before = s.predict_with_confidence(x[300:])
    s.calibrate(x[300:450], y[300:450])
    _, conf_after = s.predict_with_confidence(x[450:])
    assert conf_after.mean() <= conf_before.mean() + 1e-9


def test_jev_backend_with_fake_client() -> None:
    pytest.importorskip("typesafe_sdk")  # SDK is optional; skip if not installed

    class Choice:
        choice = "urgent"

    class R:
        def __init__(self) -> None:
            self.choices = {"decision": Choice()}

    class C:
        def system_one(self, **_: object) -> R:
            return R()

    assert JevBackend(C()).choose("down", ["low", "urgent"], "how urgent?") == "urgent"
