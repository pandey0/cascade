import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from cascade.artifact import (
    ArtifactMeta,
    create_app_from_env,
    load_artifact,
    make_teacher,
    save_artifact,
    sentence_embedder,
)
from cascade.students import LogisticStudent

from .fakes import make_teacher as fake_teacher


def _meta(**kw: object) -> ArtifactMeta:
    base = {
        "decision": "demo",
        "labels": ["a", "b"],
        "alpha": 0.1,
        "delta": 0.1,
        "threshold": 0.6,
        "embedder": "none",
        "instructions": "x",
        "teacher_provider": "claude",
        "teacher_model": "m",
        "price_in_per_m": 0.1,
        "price_out_per_m": 0.5,
        "audit_rate": 0.0,
        "shadow": False,
    }
    return ArtifactMeta(**{**base, **kw})  # type: ignore[arg-type]


def _student() -> LogisticStudent:
    rng = np.random.default_rng(0)
    x = np.vstack([rng.normal(-2, 0.5, (40, 3)), rng.normal(2, 0.5, (40, 3))])
    y = np.array(["a"] * 40 + ["b"] * 40)
    return LogisticStudent(max_iter=200).fit(x, y)


def test_roundtrip_preserves_predictions(tmp_path: Path) -> None:
    s = _student()
    save_artifact(tmp_path / "art", _meta(), s)
    meta, loaded = load_artifact(tmp_path / "art")
    x = np.array([[2.0, 2.0, 2.0], [-2.0, -2.0, -2.0]])
    p0, c0 = s.predict_with_confidence(x)
    p1, c1 = loaded.predict_with_confidence(x)
    assert p0.tolist() == p1.tolist() == ["b", "a"] and np.allclose(c0, c1)
    assert (
        meta.decision == "demo"
        and "api" not in (tmp_path / "art" / "artifact.json").read_text().lower()
    )


def test_serve_from_env_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    save_artifact(tmp_path / "art", _meta(), _student())
    monkeypatch.setenv("CASCADE_ARTIFACT_DIR", str(tmp_path / "art"))
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "audit.db"))
    monkeypatch.setenv("CASCADE_API_KEYS", "k")
    app = create_app_from_env(
        embed=lambda t: np.array([2.0, 2.0, 2.0] if "pos" in t else [0.0, 0.0, 0.0]),
        teacher=fake_teacher("a"),
    )
    c = TestClient(app)
    hi = c.post("/v1/decide", json={"decision": "demo", "input": "pos"}, headers={"X-API-Key": "k"})
    lo = c.post(
        "/v1/decide", json={"decision": "demo", "input": "neutral"}, headers={"X-API-Key": "k"}
    )
    assert hi.json()["path"] == "cheap" and hi.json()["label"] == "b"
    assert lo.json()["path"] == "teacher" and lo.json()["label"] == "a"


def test_unknown_provider_rejected() -> None:
    with pytest.raises(ValueError, match="unknown teacher provider"):
        make_teacher(_meta(teacher_provider="nope"))


def test_hashing_embedder_is_deterministic_unit_norm_and_text_sensitive() -> None:
    e = sentence_embedder("hashing:128")
    a, b = e("where is my card"), e("where is my card")
    c = e("totally different words here")
    assert a.shape == (128,) and np.allclose(a, b)
    assert abs(float(np.linalg.norm(a)) - 1.0) < 1e-9 and not np.allclose(a, c)
    assert float(np.linalg.norm(e(""))) == 0.0  # empty text -> zero vector, no crash


def test_old_artifact_without_timeout_field_still_loads(tmp_path: Path) -> None:
    save_artifact(tmp_path / "art", _meta(), _student())
    path = tmp_path / "art" / "artifact.json"
    data = json.loads(path.read_text())
    data.pop("teacher_timeout_s")
    path.write_text(json.dumps(data))
    meta, _ = load_artifact(tmp_path / "art")
    assert meta.teacher_timeout_s == 10.0  # default
