"""Build a deployable artifact (hashing embedder, Banking77) for the container/cluster smoke test.

Real data, weak features: accuracy is lower than the MiniLM student; this artifact exists to
prove the packaged service and chart work, not to benchmark.
Usage: python scripts/build_demo_artifact.py OUT_DIR
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("HF_HOME", str(ROOT / "data" / "cache" / "hf"))

from cascade.artifact import ArtifactMeta, hashing_embedder, save_artifact  # noqa: E402
from cascade.data import two_way_split  # noqa: E402
from cascade.datasets_io import load_task  # noqa: E402
from cascade.gates import select_holm  # noqa: E402
from cascade.students import LogisticStudent  # noqa: E402

N_FEATURES = 1024


def main(out: str) -> None:
    texts, y, names = load_task("banking77")
    labels = np.array([names[int(i)] for i in y])
    embed = hashing_embedder(N_FEATURES)
    x = np.vstack([embed(t) for t in texts])
    tr, po = two_way_split(texts, 0.5, 0)
    student = LogisticStudent(c=10.0, max_iter=300, seed=0).fit(x[tr], labels[tr])
    pred, conf = student.predict_with_confidence(x[po])
    gate = select_holm(conf, (pred != labels[po]).astype(np.float64), 0.10, 0.1)
    print(
        f"pool accuracy {float((pred == labels[po]).mean()):.3f}; threshold {gate.threshold}; "
        f"coverage {gate.coverage:.3f}"
    )
    meta = ArtifactMeta(
        decision="banking77",
        labels=list(names),
        alpha=0.10,
        delta=0.1,
        threshold=gate.threshold,
        embedder=f"hashing:{N_FEATURES}",
        instructions="Classify the banking message.",
        teacher_provider="claude",
        teacher_model="claude-haiku-5-5",
        price_in_per_m=0.10,
        price_out_per_m=0.50,
        audit_rate=0.0,
        shadow=False,
        created_by="scripts/build_demo_artifact.py",
    )
    save_artifact(out, meta, student)


if __name__ == "__main__":
    main(sys.argv[1])
