"""Experiment 1a data preparation: download, embed, train a student, cache score/error pools.

Teacher = gold labels (so "agreement" means correctness). Requires the `bench` extra and a CPU
PyTorch build. Writes data/cache/pools_<task>_seed<k>.npz with arrays `scores` and `errors`.
Datasets: PolyAI/banking77 (CC-BY-4.0 per HF card), clinc/clinc_oos "plus" (CC-BY-3.0 per HF card);
cite the original papers when reporting results (see docs/REFERENCES.md).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(ROOT / "data" / "cache" / "hf"))

import numpy as np  # noqa: E402
from datasets import concatenate_datasets, load_dataset  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from cascade.data import two_way_split  # noqa: E402
from cascade.students import LogisticStudent  # noqa: E402

CACHE = ROOT / "data" / "cache"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_task(task: str) -> tuple[list[str], np.ndarray]:
    if task == "banking77":
        ds = load_dataset("PolyAI/banking77")
        texts = list(ds["train"]["text"]) + list(ds["test"]["text"])
        labels = np.array(list(ds["train"]["label"]) + list(ds["test"]["label"]))
        return texts, labels
    ds = load_dataset("clinc/clinc_oos", "plus")
    names = ds["train"].features["intent"].names
    oos = names.index("oos")
    allsplits = concatenate_datasets([ds["train"], ds["validation"], ds["test"]])
    keep = [i for i, y in enumerate(allsplits["intent"]) if y != oos]
    sub = allsplits.select(keep)
    return list(sub["text"]), np.array(sub["intent"])


def main(tasks: list[str], seeds: list[int]) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    model = SentenceTransformer(MODEL, device="cpu")
    summary: dict[str, object] = {"embedding_model": MODEL, "tasks": {}}
    for task in tasks:
        texts, y = load_task(task)
        emb_path = CACHE / f"emb_{task}.npy"
        if emb_path.exists():
            x = np.load(emb_path)
        else:
            t0 = time.time()
            x = model.encode(
                texts, batch_size=128, normalize_embeddings=True, show_progress_bar=False
            )
            np.save(emb_path, x)
            print(f"[{task}] embedded {len(texts)} texts in {time.time() - t0:.0f}s", flush=True)
        for seed in seeds:
            train_idx, pool_idx = two_way_split(texts, 0.5, seed)
            t0 = time.time()
            student = LogisticStudent(c=10.0, max_iter=300, seed=seed).fit(
                x[train_idx], y[train_idx]
            )
            pred, conf = student.predict_with_confidence(x[pool_idx])
            errors = (pred != y[pool_idx]).astype(np.float64)
            np.savez(CACHE / f"pools_{task}_seed{seed}.npz", scores=conf, errors=errors)
            acc = 1.0 - float(errors.mean())
            print(
                f"[{task}] seed {seed}: train {len(train_idx)}, pool {len(pool_idx)}, "
                f"pool accuracy {acc:.4f}, fit {time.time() - t0:.0f}s",
                flush=True,
            )
            summary["tasks"].setdefault(task, []).append(  # type: ignore[union-attr]
                {"seed": seed, "train": len(train_idx), "pool": len(pool_idx), "pool_accuracy": acc}
            )
    (CACHE / "exp1a_prepare_summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main(
        sys.argv[1].split(",") if len(sys.argv) > 1 else ["banking77", "clinc150"],
        [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [0, 1, 2],
    )
