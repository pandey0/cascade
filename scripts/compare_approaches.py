"""Head-to-head: LLM only vs small model (human labels / LLM labels) vs Cascade vs semantic cache.

Plan and expectations (written before running): docs/notes/comparison-plan.md. Uses only cached
embeddings and the already-paid Claude Haiku 5.5 labels (no API calls). Accuracy is always measured
against the dataset's labels. Writes results/compare_<task>.json and a provenance manifest.

Usage: python scripts/compare_approaches.py [--tasks banking77,clinc150] [--seeds 0,1,2] [--fast]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("HF_HOME", str(ROOT / "data" / "cache" / "hf"))

from cascade.data import normalize, two_way_split  # noqa: E402
from cascade.datasets_io import load_task  # noqa: E402
from cascade.gates import select_holm  # noqa: E402
from cascade.provenance import build_manifest, record_run  # noqa: E402
from cascade.students import LogisticStudent  # noqa: E402

CACHE = ROOT / "data" / "cache"
MODEL = "claude-haiku-5-5"
AUDIT_RATE, DELTA, CALIB, DRAWS = 0.05, 0.1, 400, 100
TAUS = (0.98, 0.95, 0.92, 0.90, 0.85, 0.80, 0.70)


def load(task: str):  # type: ignore[no-untyped-def]
    texts, gold_int, names = load_task(task)
    x = np.load(CACHE / f"emb_{task}.npy")
    path = CACHE / "teacher" / f"teacher_{task}_claude_{MODEL}_n2000_seed0.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    idx = np.array([r["idx"] for r in rows])
    teacher = np.array([r["teacher"] for r in rows])
    gold_all = np.array([names[int(g)] for g in gold_int])
    c_t = sum(r["usd"] for r in rows) / len(rows)
    lat = float(np.median([r["ms"] for r in rows]))
    return texts, x, idx, teacher, gold_all, c_t, lat


def fit_predict(x_tr, y_tr, x_ev, seed):  # type: ignore[no-untyped-def]
    stu = LogisticStudent(c=10.0, max_iter=300, seed=seed).fit(x_tr, y_tr)
    return stu.predict_with_confidence(x_ev)


def cascade_stats(  # noqa: PLR0917
    conf, pred, gold, teacher, alpha, rng
):  # type: ignore[no-untyped-def]
    """Mean over audit draws: deploy rate, coverage, end-to-end accuracy, LLM calls per request."""
    n = len(conf)
    err_t = (pred != teacher).astype(float)
    dep, cov, acc, calls = [], [], [], []
    for _ in range(DRAWS):
        c = rng.choice(n, size=CALIB, replace=False)
        res = select_holm(conf[c], err_t[c], alpha, DELTA)
        if res.threshold is None:
            dep.append(0.0)
            cov.append(0.0)
            acc.append(float((teacher == gold).mean()))
            calls.append(1.0)
            continue
        acc_mask = conf >= res.threshold
        correct = np.where(acc_mask, pred == gold, teacher == gold)
        dep.append(1.0)
        cov.append(float(acc_mask.mean()))
        acc.append(float(correct.mean()))
        calls.append(float((1 - acc_mask.mean()) + acc_mask.mean() * AUDIT_RATE))
    return {
        "deploy": float(np.mean(dep)),
        "coverage": float(np.mean(cov)),
        "e2e_accuracy": float(np.mean(acc)),
        "llm_calls_per_request": float(np.mean(calls)),
    }


def semantic_cache(  # noqa: PLR0917
    xp, xseed, seed_labels, tp, gold_p, rng
):  # type: ignore[no-untyped-def]
    out = {}
    order = rng.permutation(len(xp))
    for tau in TAUS:
        cx, cy = list(xseed), list(seed_labels)
        cache = np.array(cx)
        hits = hit_correct = correct = 0
        for i in order:
            sims = cache @ xp[i]
            j = int(np.argmax(sims))
            if sims[j] >= tau:
                hits += 1
                lab = cy[j]
                hit_correct += lab == gold_p[i]
                correct += lab == gold_p[i]
            else:
                correct += tp[i] == gold_p[i]
                cache = np.vstack([cache, xp[i]])
                cy.append(tp[i])
        n = len(order)
        out[str(tau)] = {
            "hit_rate": hits / n,
            "accuracy": correct / n,
            "accuracy_on_hits": (hit_correct / hits) if hits else None,
            "llm_calls_per_request": 1 - hits / n,
        }
    return out


def run_task(task: str, seeds: list[int], fast: bool) -> dict:  # type: ignore[type-arg]
    texts, x, idx, teacher, gold_all, c_t, lat = load(task)
    gold_l = gold_all[idx]
    l_texts = [texts[i] for i in idx]
    outside = np.setdiff1d(np.arange(len(texts)), idx)
    n_gold = (50, 200, 1000) if fast else (50, 100, 200, 500, 1000, 3000, 5000)
    n_dist = (200, 1000) if fast else (50, 100, 200, 500, 1000)
    res = {"task": task, "c_t": c_t, "llm_median_latency_ms": lat, "seeds": {}}
    for seed in seeds:
        rng = np.random.default_rng(1000 + seed)
        tr, po = two_way_split(l_texts, 0.5, seed)
        xp, gp, tp = x[idx[po]], gold_l[po], teacher[po]
        pool_norm = {normalize(texts[i]) for i in idx[po]}
        keep = np.array([i for i in outside if normalize(texts[i]) not in pool_norm])
        s = {
            "llm_only_accuracy": float((tp == gp).mean()),
            "pool": len(po),
            "gold": {},
            "distilled": {},
            "cache": {},
        }
        for n in n_gold:
            sel = rng.choice(keep, size=min(n, len(keep)), replace=False)
            pred, conf = fit_predict(x[sel], gold_all[sel], xp, seed)
            entry = {"alone_accuracy": float((pred == gp).mean())}
            for a in (0.05, 0.10):
                entry[f"cascade_alpha{a}"] = cascade_stats(conf, pred, gp, tp, a, rng)
            s["gold"][str(n)] = entry
            print(f"[{task} s{seed}] gold N={n}: alone {entry['alone_accuracy']:.3f}", flush=True)
        for n in n_dist:
            sel = rng.choice(tr, size=min(n, len(tr)), replace=False)
            pred, conf = fit_predict(x[idx[sel]], teacher[sel], xp, seed)
            entry = {"alone_accuracy": float((pred == gp).mean())}
            for a in (0.05, 0.10):
                entry[f"cascade_alpha{a}"] = cascade_stats(conf, pred, gp, tp, a, rng)
            s["distilled"][str(n)] = entry
            print(
                f"[{task} s{seed}] distilled N={n}: alone {entry['alone_accuracy']:.3f}", flush=True
            )
        s["cache"] = semantic_cache(xp, x[idx[tr]], list(teacher[tr]), tp, gp, rng)
        res["seeds"][str(seed)] = s
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="banking77,clinc150")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "results"))
    a = ap.parse_args()
    started = time.time()
    outs = []
    for task in a.tasks.split(","):
        res = run_task(task, [int(v) for v in a.seeds.split(",")], a.fast)
        p = Path(a.out) / f"compare_{task}{'_fast' if a.fast else ''}.json"
        p.write_text(json.dumps(res, indent=2), encoding="utf-8")
        outs.append(p)
    man = build_manifest(
        "compare_approaches" + ("_fast" if a.fast else ""),
        ["compare_approaches", *sys.argv[1:]],
        ROOT,
        [],
        outs,
        started,
        {"audit_rate": AUDIT_RATE, "delta": DELTA, "calibration": CALIB, "draws": DRAWS},
    )
    record_run(
        man,
        ROOT / "evidence" / "manifests" / f"{man['name']}.manifest.json",
        ROOT / "evidence" / "ledger.csv",
    )


if __name__ == "__main__":
    main()
