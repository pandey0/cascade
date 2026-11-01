"""Label a seeded sample of a benchmark with a Gemini teacher (exp1b data step).

Safe by default: without ``--run`` it only prints an estimated cost (no network, no key needed).
The key is read from GEMINI_API_KEY (export it, or put it in a gitignored .env). Results are
cached in SQLite, so re-runs never re-bill; ``--max-usd`` is a hard cap on new spend.

Example:
  python scripts/label_with_teacher.py --task banking77 --n 20 --model gemini-3.5-flash-lite \
      --price-in 0.10 --price-out 0.40            # dry run (prices: copy from the pricing page)
  ... --run                                       # real calls
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

from cascade.adapters.claude import ClaudeConfig, ClaudeTeacher  # noqa: E402
from cascade.adapters.gemini import (  # noqa: E402
    INVALID_LABEL,
    GeminiConfig,
    GeminiTeacher,
    build_system_instruction,
)
from cascade.datasets_io import load_task  # noqa: E402
from cascade.provenance import build_manifest, record_run  # noqa: E402
from cascade.teacher import BudgetExceededError, CachedTeacher  # noqa: E402

INSTRUCTIONS = {
    "banking77": "Classify the customer message from a banking app into exactly one intent.",
    "clinc150": "Classify the user request to a voice assistant into exactly one intent.",
}


def load_env_file(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE lines); never prints values."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=["banking77", "clinc150"], required=True)
    ap.add_argument("--n", type=int, required=True, help="sample size")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--provider", choices=["claude", "gemini"], default="claude")
    ap.add_argument("--model", required=True, help="exact model id")
    ap.add_argument("--price-in", type=float, required=True, help="USD per 1M input tokens")
    ap.add_argument("--price-out", type=float, required=True, help="USD per 1M output tokens")
    ap.add_argument("--thinking", default="MINIMAL")
    ap.add_argument("--max-usd", type=float, default=1.0)
    ap.add_argument("--min-interval", type=float, default=0.0, help="seconds between calls")
    ap.add_argument("--prompt-version", default="v1")
    ap.add_argument("--run", action="store_true", help="make real API calls")
    ap.add_argument("--name", default=None)
    args = ap.parse_args()

    texts, gold, names = load_task(args.task)
    rng = np.random.default_rng(args.seed)
    idx = np.sort(rng.choice(len(texts), size=min(args.n, len(texts)), replace=False))
    common = {
        "model": args.model,
        "labels": tuple(names),
        "instructions": INSTRUCTIONS[args.task],
        "price_in_per_m": args.price_in,
        "price_out_per_m": args.price_out,
        "min_interval_s": args.min_interval,
    }
    cfg = (
        ClaudeConfig(**common)
        if args.provider == "claude"
        else GeminiConfig(**common, thinking_level=args.thinking)
    )
    sys_chars = len(build_system_instruction(cfg))
    est_in = sum((sys_chars + len(texts[i])) / 4 for i in idx)  # ~4 chars/token, rough
    est_out = 12.0 * len(idx)  # short JSON; thinking tokens at MINIMAL are small but not zero
    est = (est_in * args.price_in + est_out * args.price_out) / 1e6
    print(f"{args.task}: n={len(idx)} est input tokens~{est_in:,.0f} est cost~${est:.4f} (rough)")
    if not args.run:
        print("dry run; add --run to call the API")
        return 0

    load_env_file(ROOT / ".env")
    out_dir = ROOT / "data" / "cache" / "teacher"
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    teacher = CachedTeacher(
        ClaudeTeacher(cfg) if args.provider == "claude" else GeminiTeacher(cfg),
        out_dir / "cache.sqlite",
        model_id=args.model,
        prompt_version=args.prompt_version,
        max_usd=args.max_usd,
    )
    rows = []
    try:
        for i in idx:
            r = teacher(texts[i])
            rows.append(
                {
                    "idx": int(i),
                    "gold": names[int(gold[i])],
                    "teacher": r.label,
                    "in": r.input_tokens,
                    "out": r.output_tokens,
                    "usd": r.cost_usd,
                    "ms": r.latency_ms,
                }
            )
    except BudgetExceededError as exc:
        print(f"STOPPED: {exc}")
    finally:
        teacher.close()
    stem = (
        args.name or f"teacher_{args.task}_{args.provider}_{args.model}_n{len(idx)}_seed{args.seed}"
    )
    out = out_dir / f"{stem}.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    done = len(rows)
    valid = [r for r in rows if r["teacher"] != INVALID_LABEL]
    acc = sum(r["teacher"] == r["gold"] for r in valid) / max(len(valid), 1)
    print(
        f"labelled {done}/{len(idx)}; invalid={done - len(valid)}; teacher-vs-gold={acc:.3f}; "
        f"new spend=${teacher.spent_usd:.4f}; cache hits={teacher.hits}"
    )
    manifest = build_manifest(
        stem,
        ["label_with_teacher", *sys.argv[1:]],
        ROOT,
        [],
        [out],
        started,
        {
            "model": args.model,
            "task": args.task,
            "n": done,
            "spent_usd": teacher.spent_usd,
            "prompt_version": args.prompt_version,
            "thinking": args.thinking,
        },
    )
    record_run(
        manifest,
        ROOT / "evidence" / "manifests" / f"{stem}.manifest.json",
        ROOT / "evidence" / "ledger.csv",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
