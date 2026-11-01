"""Experiment 2 data preparation: pre-/post-shift pools built from real embeddings.

Teacher = gold labels (isolates drift from teacher noise; exp1b covers noise). For each task:
  base:      student trained on the train half, pool = held-out half (as exp1a, seed 0).
  prior:     post pool resamples the pool with 5x weight on the hardest 20% of classes.
  unseen:    student trained WITHOUT 15% of the classes; pre pool = seen-class items only;
             post pool = 50% unseen-class items (student can only be wrong on them).
  perturbed: post pool = same items with ~15% of words corrupted (char delete/swap), re-embedded.
Saves data/cache/drift_<task>_<shift>.npz with pre_scores, pre_errors, post_scores, post_errors.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("HF_HOME", str(ROOT / "data" / "cache" / "hf"))

from sentence_transformers import SentenceTransformer  # noqa: E402

from cascade.data import two_way_split  # noqa: E402
from cascade.datasets_io import load_task  # noqa: E402
from cascade.students import LogisticStudent  # noqa: E402

CACHE = ROOT / "data" / "cache"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SEED = 0


def corrupt(text: str, rng: np.random.Generator, p: float = 0.15) -> str:
    words = text.split()
    for i, w in enumerate(words):
        if len(w) > 3 and rng.random() < p:
            j = int(rng.integers(1, len(w) - 1))
            words[i] = (
                w[:j] + w[j + 1 :] if rng.random() < 0.5 else w[:j] + w[j + 1] + w[j] + w[j + 2 :]
            )
    return " ".join(words)


def main(tasks: list[str]) -> None:
    rng = np.random.default_rng(SEED)
    encoder = SentenceTransformer(MODEL, device="cpu")
    for task in tasks:
        texts, y, _names = load_task(task)
        x = np.load(CACHE / f"emb_{task}.npy")
        tr, po = two_way_split(texts, 0.5, SEED)
        # --- base student, prior shift, perturbation
        stu = LogisticStudent(c=10.0, max_iter=300, seed=SEED).fit(x[tr], y[tr])
        pred, conf = stu.predict_with_confidence(x[po])
        err = (pred != y[po]).astype(np.float64)
        cls_err = {c: err[y[po] == c].mean() for c in np.unique(y[po])}
        hard = sorted(cls_err, key=lambda c: -cls_err[c])[: max(1, len(cls_err) // 5)]
        w = np.where(np.isin(y[po], hard), 5.0, 1.0)
        w /= w.sum()
        draw = rng.choice(len(po), size=len(po), replace=True, p=w)
        np.savez(
            CACHE / f"drift_{task}_prior.npz",
            pre_scores=conf,
            pre_errors=err,
            post_scores=conf[draw],
            post_errors=err[draw],
        )
        sub = rng.choice(len(po), size=min(3000, len(po)), replace=False)
        noisy = encoder.encode(
            [corrupt(texts[po[i]], rng) for i in sub],
            batch_size=128,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        pn, cn = stu.predict_with_confidence(noisy)
        np.savez(
            CACHE / f"drift_{task}_perturbed.npz",
            pre_scores=conf,
            pre_errors=err,
            post_scores=cn,
            post_errors=(pn != y[po][sub]).astype(np.float64),
        )
        # --- unseen classes
        classes = np.unique(y)
        unseen = rng.choice(classes, size=max(1, int(0.15 * len(classes))), replace=False)
        keep_tr = tr[~np.isin(y[tr], unseen)]
        stu_u = LogisticStudent(c=10.0, max_iter=300, seed=SEED).fit(x[keep_tr], y[keep_tr])
        pu, cu = stu_u.predict_with_confidence(x[po])
        eu = (pu != y[po]).astype(np.float64)
        seen_mask = ~np.isin(y[po], unseen)
        seen_idx, unseen_idx = np.where(seen_mask)[0], np.where(~seen_mask)[0]
        n_post = 3000
        mix = np.concatenate(
            [rng.choice(seen_idx, n_post // 2), rng.choice(unseen_idx, n_post - n_post // 2)]
        )
        np.savez(
            CACHE / f"drift_{task}_unseen.npz",
            pre_scores=cu[seen_idx],
            pre_errors=eu[seen_idx],
            post_scores=cu[mix],
            post_errors=eu[mix],
        )
        print(
            f"[{task}] base acc {1 - err.mean():.3f}; prior-shift acc {1 - err[draw].mean():.3f}; "
            f"perturbed acc {1 - (pn != y[po][sub]).mean():.3f}; unseen: pre acc "
            f"{1 - eu[seen_idx].mean():.3f}, post acc {1 - eu[mix].mean():.3f}",
            flush=True,
        )


if __name__ == "__main__":
    main(sys.argv[1].split(",") if len(sys.argv) > 1 else ["banking77", "clinc150"])
