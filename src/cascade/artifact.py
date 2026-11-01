"""Deployable artifact: a student, its certified threshold and the settings to serve it.

Layout of an artifact directory: ``artifact.json`` (settings, no secrets) + ``student.npz``
(plain arrays; loaded with ``allow_pickle=False``).
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from fastapi import FastAPI
from numpy.typing import NDArray

from cascade.adapters.claude import ClaudeConfig, ClaudeTeacher
from cascade.adapters.gemini import GeminiConfig, GeminiTeacher
from cascade.engine import Engine, EngineConfig
from cascade.gateway.app import Settings, configure_logging, create_app
from cascade.store import AuditStore
from cascade.students import LogisticStudent, load_student, save_student
from cascade.teacher import TeacherResponse

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class ArtifactMeta:
    decision: str
    labels: list[str]
    alpha: float
    delta: float
    threshold: float | None
    embedder: str  # sentence-transformers model id, or "hashing:<n_features>"
    instructions: str
    teacher_provider: str  # "claude" | "gemini"
    teacher_model: str
    price_in_per_m: float
    price_out_per_m: float
    audit_rate: float = 0.02
    shadow: bool = True
    created_by: str = ""
    teacher_timeout_s: float = 10.0  # request-path wait and the adapters' HTTP timeout
    teacher_workers: int = 32  # concurrent request-path teacher calls
    audit_workers: int = 2  # background audit threads
    audit_queue_size: int = 256  # pending audits before new ones are dropped


def save_artifact(path: str | Path, meta: ArtifactMeta, student: LogisticStudent) -> None:
    d = Path(path)
    d.mkdir(parents=True, exist_ok=True)
    (d / "artifact.json").write_text(json.dumps(asdict(meta), indent=2), encoding="utf-8")
    save_student(student, str(d / "student.npz"))


def load_artifact(path: str | Path) -> tuple[ArtifactMeta, LogisticStudent]:
    d = Path(path)
    meta = ArtifactMeta(**json.loads((d / "artifact.json").read_text(encoding="utf-8")))
    return meta, load_student(str(d / "student.npz"))


def make_teacher(meta: ArtifactMeta) -> Callable[[str], TeacherResponse]:
    common = {
        "model": meta.teacher_model,
        "labels": tuple(meta.labels),
        "instructions": meta.instructions,
        "price_in_per_m": meta.price_in_per_m,
        "price_out_per_m": meta.price_out_per_m,
        "timeout_s": meta.teacher_timeout_s,
    }
    if meta.teacher_provider == "claude":
        return ClaudeTeacher(ClaudeConfig(**common))  # type: ignore[arg-type]
    if meta.teacher_provider == "gemini":
        return GeminiTeacher(GeminiConfig(**common))  # type: ignore[arg-type]
    msg = f"unknown teacher provider: {meta.teacher_provider}"
    raise ValueError(msg)


def hashing_embedder(n_features: int) -> Callable[[str], FloatArray]:
    """Dependency-free embedder (hashed word + bigram counts, L2-normalised). Weaker than a
    sentence encoder, but needs no PyTorch and no model download: fits the default image."""
    from sklearn.feature_extraction.text import HashingVectorizer  # noqa: PLC0415

    vec = HashingVectorizer(
        n_features=n_features, alternate_sign=False, norm="l2", ngram_range=(1, 2), lowercase=True
    )

    def embed(text: str) -> FloatArray:
        return np.asarray(vec.transform([text]).toarray()[0], dtype=np.float64)

    return embed


def sentence_embedder(model_id: str) -> Callable[[str], FloatArray]:
    if model_id.startswith("hashing:"):
        return hashing_embedder(int(model_id.split(":", 1)[1]))
    from sentence_transformers import SentenceTransformer  # noqa: PLC0415  (optional extra)

    encoder = SentenceTransformer(model_id, device="cpu")

    def embed(text: str) -> FloatArray:
        return np.asarray(encoder.encode([text], normalize_embeddings=True)[0], dtype=np.float64)

    return embed


def create_app_from_env(
    embed: Callable[[str], FloatArray] | None = None,
    teacher: Callable[[str], TeacherResponse] | None = None,
) -> FastAPI:
    """Uvicorn factory: ``uvicorn --factory cascade.artifact:create_app_from_env``.

    Env: CASCADE_ARTIFACT_DIR (required), CASCADE_DB_PATH (default ./audit.db), CASCADE_API_KEYS,
    CASCADE_ALLOW_ANONYMOUS, and the teacher provider's key (e.g. ANTHROPIC_API_KEY).
    ``embed``/``teacher`` can be injected (tests).
    """
    configure_logging()
    meta, student = load_artifact(os.environ["CASCADE_ARTIFACT_DIR"])
    store = AuditStore(os.environ.get("CASCADE_DB_PATH", "audit.db"))
    cfg = EngineConfig(
        decision=meta.decision,
        alpha=meta.alpha,
        delta=meta.delta,
        audit_rate=meta.audit_rate,
        shadow=meta.shadow,
        teacher_timeout_s=meta.teacher_timeout_s,
        teacher_workers=meta.teacher_workers,
        audit_workers=meta.audit_workers,
        audit_queue_size=meta.audit_queue_size,
    )
    engine = Engine(
        cfg,
        embed or sentence_embedder(meta.embedder),
        student,
        teacher or make_teacher(meta),
        store,
        meta.threshold,
    )
    return create_app({meta.decision: engine}, Settings.from_env(), store)
