"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from cascade import __version__
from cascade.bench import aggregate_pools, run_pool_experiment, to_markdown_ranges
from cascade.provenance import build_manifest, record_run
from cascade.sim import run_exp0, to_markdown


def main(argv: list[str] | None = None) -> int:  # noqa: PLR0915
    parser = argparse.ArgumentParser(prog="cascade")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version")
    e0 = sub.add_parser("exp0", help="synthetic selection-bias experiment (no API calls)")
    e0.add_argument("--alpha", type=float, default=0.05)
    e0.add_argument("--delta", type=float, default=0.1)
    e0.add_argument("--trials", type=int, default=2000)
    e0.add_argument("--m", type=int, nargs="+", default=[200, 500, 1000, 5000])
    e0.add_argument("--seed", type=int, default=0)
    e0.add_argument("--out", type=Path, default=Path("results"))
    e0.add_argument("--evidence", type=Path, default=Path("evidence"))
    e0.add_argument("--name", default="exp0")
    e1 = sub.add_parser("exp1a", help="gates on cached real pools (gold labels as teacher)")
    e1.add_argument("pools", type=Path, nargs="+", help="npz files with scores/errors arrays")
    e1.add_argument("--alpha", type=float, default=0.05)
    e1.add_argument("--delta", type=float, default=0.1)
    e1.add_argument("--trials", type=int, default=500)
    e1.add_argument("--m", type=int, nargs="+", default=[250, 500, 1000, 2000])
    e1.add_argument("--seed", type=int, default=0)
    e1.add_argument("--out", type=Path, default=Path("results"))
    e1.add_argument("--name", default="exp1a")
    e1.add_argument("--evidence", type=Path, default=Path("evidence"))
    e1b = sub.add_parser(
        "exp1b", help="gates with a noisy LLM teacher; risk vs teacher and vs gold"
    )
    e1b.add_argument("pools", type=Path, nargs="+", help="npz with scores/errors/gold_errors")
    e1b.add_argument("--alpha", type=float, default=0.05)
    e1b.add_argument("--delta", type=float, default=0.1)
    e1b.add_argument("--trials", type=int, default=400)
    e1b.add_argument("--m", type=int, nargs="+", default=[100, 200, 400])
    e1b.add_argument("--seed", type=int, default=0)
    e1b.add_argument("--out", type=Path, default=Path("results"))
    e1b.add_argument("--name", default="exp1b")
    e1b.add_argument("--evidence", type=Path, default=Path("evidence"))
    e2 = sub.add_parser("exp2", help="drift streams: static vs rolling gates, monitor comparison")
    e2.add_argument("pools", type=Path, nargs="+", help="npz with pre_/post_ scores and errors")
    e2.add_argument("--alpha", type=float, default=0.05)
    e2.add_argument("--delta", type=float, default=0.1)
    e2.add_argument("--trials", type=int, default=30)
    e2.add_argument("--audit-rates", type=float, nargs="+", default=[0.02, 0.05, 0.10])
    e2.add_argument("--n-pre", type=int, default=3000)
    e2.add_argument("--n-post", type=int, default=6000)
    e2.add_argument("--window", type=int, default=1000)
    e2.add_argument("--recal-every", type=int, default=250)
    e2.add_argument("--initial-labels", type=int, default=2000)
    e2.add_argument("--workers", type=int, default=4)
    e2.add_argument("--seed", type=int, default=0)
    e2.add_argument("--out", type=Path, default=Path("results"))
    e2.add_argument("--name", default="exp2")
    e2.add_argument("--evidence", type=Path, default=Path("evidence"))
    args = parser.parse_args(argv)
    if args.cmd == "version":
        print(__version__)
        return 0
    if args.cmd == "exp1a":
        return _exp1a(args, argv)
    if args.cmd == "exp1b":
        return _exp1b(args, argv)
    if args.cmd == "exp2":
        return _exp2(args, argv)
    started = time.time()
    rows = run_exp0(args.m, args.trials, args.alpha, args.delta, args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    jpath, mpath = args.out / f"{args.name}.json", args.out / f"{args.name}.md"
    jpath.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    md = to_markdown(rows, args.alpha, args.delta)
    mpath.write_text(md, encoding="utf-8")
    print(md)
    _record(args, argv, started, [], [jpath, mpath], {"alpha": args.alpha, "delta": args.delta})
    return 0


def _record(  # noqa: PLR0917
    args: argparse.Namespace,
    argv: list[str] | None,
    started: float,
    inputs: list[Path],
    outputs: list[Path],
    extra: dict[str, object],
) -> None:
    command = ["cascade", *(sys.argv[1:] if argv is None else argv)]
    manifest = build_manifest(args.name, command, Path.cwd(), inputs, outputs, started, extra)
    record_run(
        manifest,
        args.evidence / "manifests" / f"{args.name}.manifest.json",
        args.evidence / "ledger.csv",
    )


def _exp1a(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    started = time.time()
    per_pool = []
    for path in args.pools:
        data = np.load(path)
        per_pool.append(
            run_pool_experiment(
                data["scores"],
                data["errors"],
                args.m,
                args.trials,
                args.alpha,
                args.delta,
                args.seed,
            )
        )
    rows = aggregate_pools(per_pool)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"{args.name}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    md = to_markdown_ranges(rows, args.alpha, args.delta)
    (args.out / f"{args.name}.md").write_text(md, encoding="utf-8")
    print(md)
    _record(
        args,
        argv,
        started,
        list(args.pools),
        [args.out / f"{args.name}.json", args.out / f"{args.name}.md"],
        {"alpha": args.alpha, "delta": args.delta, "trials": args.trials, "sizes": args.m},
    )
    return 0


def _drift_job(job: tuple[Any, ...]) -> dict[str, Any]:
    from cascade.drift import DriftConfig, simulate_stream  # noqa: PLC0415

    path, policy, rate, seed, a = job
    data = np.load(path)
    cfg = DriftConfig(
        alpha=a["alpha"],
        delta=a["delta"],
        audit_rate=rate,
        window_labels=a["window"],
        recal_every=a["recal_every"],
        initial_labels=a["initial_labels"],
    )
    return simulate_stream(
        (data["pre_scores"], data["pre_errors"]),
        (data["post_scores"], data["post_errors"]),
        a["n_pre"],
        a["n_post"],
        policy,
        cfg,
        seed,
    )


def _exp2(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    from concurrent.futures import ProcessPoolExecutor  # noqa: PLC0415

    from cascade.drift import summarise_trials  # noqa: PLC0415

    started = time.time()
    shared = {
        "alpha": args.alpha,
        "delta": args.delta,
        "window": args.window,
        "recal_every": args.recal_every,
        "initial_labels": args.initial_labels,
        "n_pre": args.n_pre,
        "n_post": args.n_post,
    }
    rows: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for path in args.pools:
            for policy in ("static_holm", "rolling_naive", "rolling_holm"):
                for rate in args.audit_rates:
                    jobs = [
                        (str(path), policy, rate, args.seed + i, shared) for i in range(args.trials)
                    ]
                    trials = list(pool.map(_drift_job, jobs))
                    rows.append(
                        {
                            "pool": Path(path).stem,
                            "policy": policy,
                            "audit_rate": rate,
                            **summarise_trials(trials, args.alpha),
                        }
                    )
    args.out.mkdir(parents=True, exist_ok=True)
    jpath, mpath = args.out / f"{args.name}.json", args.out / f"{args.name}.md"
    jpath.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    head = (
        f"alpha={args.alpha}, delta={args.delta}, {args.trials} streams per cell, "
        f"{args.n_pre} pre + {args.n_post} post decisions, window {args.window} labels.\n\n"
        "| pool | policy | audit | post risk | post cov | block viol | recovery (decisions) "
        "| false alarm CS / z | detect CS / z | delay CS / z |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
    )
    body = "\n".join(
        f"| {r['pool']} | {r['policy']} | {r['audit_rate']:.2f} | {r['post_mean_risk']:.3f} | "
        f"{r['post_mean_coverage']:.2f} | {r['post_block_violation_rate']:.2f} | "
        f"{r['median_recovery_decisions']:.0f} | "
        f"{r['false_alarm_cs']:.2f} / {r['false_alarm_z']:.2f} | "
        f"{r['detect_rate_cs']:.2f} / {r['detect_rate_z']:.2f} | "
        f"{r['median_delay_cs']:.0f} / {r['median_delay_z']:.0f} |"
        for r in rows
    )
    mpath.write_text(head + body + "\n", encoding="utf-8")
    print(head + body)
    _record(
        args, argv, started, list(args.pools), [jpath, mpath], {**shared, "trials": args.trials}
    )
    return 0


def _exp1b(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    started = time.time()
    outputs: list[Path] = []
    args.out.mkdir(parents=True, exist_ok=True)
    for target in ("teacher", "gold"):
        per_pool = []
        for path in args.pools:
            data = np.load(path)
            per_pool.append(
                run_pool_experiment(
                    data["scores"],
                    data["errors"],
                    args.m,
                    args.trials,
                    args.alpha,
                    args.delta,
                    args.seed,
                    eval_errors=data["gold_errors"] if target == "gold" else None,
                )
            )
        rows = aggregate_pools(per_pool)
        base = args.out / f"{args.name}_vs_{target}"
        base.with_suffix(".json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
        md = to_markdown_ranges(rows, args.alpha, args.delta)
        base.with_suffix(".md").write_text(md, encoding="utf-8")
        outputs += [base.with_suffix(".json"), base.with_suffix(".md")]
        print(f"== risk target: disagreement with {target}\n{md}")
    _record(
        args,
        argv,
        started,
        list(args.pools),
        outputs,
        {"alpha": args.alpha, "delta": args.delta, "trials": args.trials, "sizes": args.m},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
