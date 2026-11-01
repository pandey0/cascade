"""Aggregate results/compare_*.json into tables, a year-1 cost model by volume, and two figures.

All costs other than the measured LLM price per call are ASSUMPTIONS (printed in the output).
Writes results/compare_summary.md, docs/img/fig7_labels_vs_accuracy.png, fig8_calls_vs_accuracy.png.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HUMAN_LABEL, NODE_HOUR, NODES, STUDENT_REQ = 0.10, 0.15, 2, 0.15 / 3600 / 50
HOSTING_DAY = NODE_HOUR * 24 * NODES
ENG = {"llm": 0, "gold": 5_000, "cascade": 10_000, "cache": 3_000}
VOLUMES = (10_000, 100_000, 1_000_000, 10_000_000)


def mean(seeds: list[dict], path: list[str]) -> float:
    vals = []
    for s in seeds:
        v: object = s
        for p in path:
            v = v[p]  # type: ignore[index]
        vals.append(float("nan") if v is None else float(v))  # type: ignore[arg-type]
    return float(np.nanmean(vals))


def load(task: str) -> tuple[dict, list[dict]]:
    d = json.loads((ROOT / "results" / f"compare_{task}.json").read_text(encoding="utf-8"))
    return d, list(d["seeds"].values())


def configs(task: str) -> list[dict]:
    """Representative operating points: name, accuracy, LLM calls per request, one-time cost."""
    d, S = load(task)
    c_t = d["c_t"]
    llm = mean(S, ["llm_only_accuracy"])
    out = [
        {
            "name": "LLM only",
            "acc": llm,
            "calls": 1.0,
            "once": 0.0,
            "self": False,
            "eng": ENG["llm"],
        }
    ]
    for n in ("1000", "3000"):
        out.append(
            {
                "name": f"Small model, {n} human labels, no LLM",
                "acc": mean(S, ["gold", n, "alone_accuracy"]),
                "calls": 0.0,
                "once": int(n) * HUMAN_LABEL,
                "self": True,
                "eng": ENG["gold"],
            }
        )
    for kind, n, lab in (
        ("distilled", "1000", "Cascade, 1000 LLM labels"),
        ("gold", "3000", "Cascade, 3000 human labels"),
    ):
        p = [kind, n, "cascade_alpha0.1"]
        llm_labels = int(n) * c_t if kind == "distilled" else int(n) * HUMAN_LABEL
        out.append(
            {
                "name": f"{lab}, error target 10%",
                "acc": mean(S, [*p, "e2e_accuracy"]),
                "calls": mean(S, [*p, "llm_calls_per_request"]),
                "once": llm_labels + 400 * c_t,
                "self": True,
                "eng": ENG["cascade"],
            }
        )
    for tau in ("0.9", "0.85"):
        out.append(
            {
                "name": f"Semantic cache, similarity {tau}",
                "acc": mean(S, ["cache", tau, "accuracy"]),
                "calls": mean(S, ["cache", tau, "llm_calls_per_request"]),
                "once": 0.0,
                "self": True,
                "eng": ENG["cache"],
            }
        )
    for o in out:
        o["c_t"] = c_t
    return out


def year1(o: dict, volume: int) -> float:
    var = o["calls"] * o["c_t"] + (STUDENT_REQ if o["self"] else 0.0)
    host = HOSTING_DAY if o["self"] else 0.0
    return o["once"] + o["eng"] + 365 * (volume * var + host)


def fig_labels() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=False)
    for ax, task, title in zip(
        axes,
        ("banking77", "clinc150"),
        ("Banking77 (77 categories)", "CLINC150 (150 categories)"),
        strict=True,
    ):
        _, S = load(task)
        for kind, color, lab in (
            ("gold", "#1e8449", "trained on dataset (human) labels"),
            ("distilled", "#2471a3", "trained on the LLM's labels"),
        ):
            ns = [int(n) for n in S[0][kind]]
            ys = [mean(S, [kind, str(n), "alone_accuracy"]) for n in ns]
            ax.plot(ns, ys, "o-", color=color, label=lab)
        ax.axhline(mean(S, ["llm_only_accuracy"]), color="#c0392b", ls="--", label="the LLM alone")
        ax.set_xscale("log")
        ax.set_xlabel("number of labelled examples")
        ax.set_title(title, fontsize=10)
        ax.set_ylim(0, 1.0)
    axes[0].set_ylabel("accuracy against the dataset's labels")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=8, bbox_to_anchor=(0.5, -0.08))
    fig.suptitle(
        "A small model with no LLM at serving time: accuracy vs labels", fontsize=10, y=1.02
    )
    fig.savefig(ROOT / "docs/img/fig7_labels_vs_accuracy.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_calls() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=False)
    for ax, task, title in zip(
        axes, ("banking77", "clinc150"), ("Banking77", "CLINC150"), strict=True
    ):
        _, S = load(task)
        llm = mean(S, ["llm_only_accuracy"])
        ax.scatter([1.0], [llm], color="#c0392b", s=70, zorder=3, label="LLM only")
        taus = list(S[0]["cache"])
        ax.plot(
            [mean(S, ["cache", t, "llm_calls_per_request"]) for t in taus],
            [mean(S, ["cache", t, "accuracy"]) for t in taus],
            "s-",
            color="#8e44ad",
            label="semantic cache (similarity sweep)",
        )
        for kind, color, lab in (
            ("distilled", "#2471a3", "Cascade, LLM labels (target 10%)"),
            ("gold", "#1e8449", "Cascade, human labels (target 10%)"),
        ):
            ns = list(S[0][kind])
            ax.plot(
                [mean(S, [kind, n, "cascade_alpha0.1", "llm_calls_per_request"]) for n in ns],
                [mean(S, [kind, n, "cascade_alpha0.1", "e2e_accuracy"]) for n in ns],
                "o-",
                color=color,
                label=lab,
            )
        ax.set_xlabel("LLM calls per request (lower is cheaper)")
        ax.set_title(title, fontsize=10)
        ax.set_xlim(-0.02, 1.05)
        ax.invert_xaxis()
    axes[0].set_ylabel("end-to-end accuracy against the dataset's labels")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=8, bbox_to_anchor=(0.5, -0.1))
    fig.suptitle(
        "Fewer LLM calls vs accuracy: Cascade and a semantic cache (to the left = cheaper)",
        fontsize=10,
        y=1.02,
    )
    fig.savefig(ROOT / "docs/img/fig8_calls_vs_accuracy.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    lines = [
        "# Head-to-head comparison: summary tables (generated; do not edit)",
        "",
        f"Assumptions (NOT measured): human label ${HUMAN_LABEL:.2f}; node ${NODE_HOUR}/hour, "
        f"{NODES} nodes always on (${HOSTING_DAY:.1f}/day) for self-hosted approaches; "
        f"small-model serving ${STUDENT_REQ:.1e}/request; one-off engineering {ENG}. "
        "LLM price per call is measured. Year-1 cost = one-off labels + engineering "
        "+ 365 days of running cost.",
        "",
    ]
    for task in ("banking77", "clinc150"):
        d, _ = load(task)
        lines += [
            f"## {task} (LLM price ${d['c_t']:.6f}/call, "
            f"LLM median latency {d['llm_median_latency_ms']:.0f} ms)",
            "",
            "| approach | accuracy | LLM calls per request | "
            + " | ".join(f"year-1 cost at {v:,}/day" for v in VOLUMES)
            + " |",
            "|---|---|---|" + "---|" * len(VOLUMES),
        ]
        for o in configs(task):
            costs = " | ".join(f"${year1(o, v):,.0f}" for v in VOLUMES)
            lines.append(f"| {o['name']} | {o['acc']:.1%} | {o['calls']:.2f} | {costs} |")
        lines.append("")
    (ROOT / "results" / "compare_summary.md").write_text("\n".join(lines), encoding="utf-8")
    fig_labels()
    fig_calls()
    print("\n".join(lines))


if __name__ == "__main__":
    main()
