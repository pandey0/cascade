"""Experiment 1b data preparation: pools with a noisy LLM teacher.

Inputs: teacher labels from scripts/label_with_teacher.py (JSONL) and cached MiniLM embeddings.
For each task and seed the labelled sample L is split 50/50 (duplicate texts kept together):
  variant A "distilled": student trained on the teacher's labels for the first half of L.
  variant B "gold-trained": student trained on gold labels of all items outside L, excluding any
                            item whose normalised text also appears in the pool half.
The pool is the second half of L. Saved arrays: scores, errors (student != teacher),
gold_errors (student != gold), teacher_gold_errors (teacher != gold).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("HF_HOME", str(ROOT / "data" / "cache" / "hf"))

from cascade.data import normalize, two_way_split  # noqa: E402
from cascade.datasets_io import load_task  # noqa: E402
from cascade.students import LogisticStudent  # noqa: E402

CACHE = ROOT / "data" / "cache"
TEACHER = CACHE / "teacher"


def main(tasks: list[str], seeds: list[int], model: str) -> None:
    summary: dict[str, object] = {"teacher_model": model, "runs": []}
    for task in tasks:
        texts, gold_int, names = load_task(task)
        x = np.load(CACHE / f"emb_{task}.npy")
        assert len(x) == len(texts), "embedding rows must match dataset rows"
        rows = [
            json.loads(line)
            for line in (TEACHER / f"teacher_{task}_claude_{model}_n2000_seed0.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        idx = np.array([r["idx"] for r in rows])
        teacher = np.array([r["teacher"] for r in rows])
        gold = np.array([names[int(gold_int[i])] for i in idx])
        outside = np.setdiff1d(np.arange(len(texts)), idx)
        gold_all = np.array([names[int(g)] for g in gold_int])
        l_texts = [texts[i] for i in idx]
        for seed in seeds:
            tr, po = two_way_split(l_texts, 0.5, seed)
            # variant A: distilled from the teacher
            a = LogisticStudent(c=10.0, max_iter=300, seed=seed).fit(x[idx[tr]], teacher[tr])
            pred_a, conf_a = a.predict_with_confidence(x[idx[po]])
            # variant B: gold-trained on items outside L, minus text duplicates of the pool
            pool_norm = {normalize(texts[i]) for i in idx[po]}
            keep = np.array([i for i in outside if normalize(texts[i]) not in pool_norm])
            b = LogisticStudent(c=10.0, max_iter=300, seed=seed).fit(x[keep], gold_all[keep])
            pred_b, conf_b = b.predict_with_confidence(x[idx[po]])
            for variant, pred, conf in (
                ("distilled", pred_a, conf_a),
                ("goldtrained", pred_b, conf_b),
            ):
                np.savez(
                    CACHE / f"pools1b_{variant}_{task}_seed{seed}.npz",
                    scores=conf,
                    errors=(pred != teacher[po]).astype(np.float64),
                    gold_errors=(pred != gold[po]).astype(np.float64),
                    teacher_gold_errors=(teacher[po] != gold[po]).astype(np.float64),
                )
                rec = {
                    "task": task,
                    "seed": seed,
                    "variant": variant,
                    "train": int(len(tr) if variant == "distilled" else len(keep)),
                    "pool": len(po),
                    "agree_with_teacher": float((pred == teacher[po]).mean()),
                    "agree_with_gold": float((pred == gold[po]).mean()),
                    "teacher_vs_gold": float((teacher[po] == gold[po]).mean()),
                }
                summary["runs"].append(rec)  # type: ignore[union-attr]
                print(rec, flush=True)
    (CACHE / "exp1b_prepare_summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main(
        sys.argv[1].split(",") if len(sys.argv) > 1 else ["banking77", "clinc150"],
        [int(v) for v in sys.argv[2].split(",")] if len(sys.argv) > 2 else [0, 1, 2],
        sys.argv[3] if len(sys.argv) > 3 else "claude-haiku-5-5",
    )
