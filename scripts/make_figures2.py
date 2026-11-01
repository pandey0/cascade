"""Figures for the teacher-noise (exp1b) and drift (exp2) studies, generated from results/*.json."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUTS = [ROOT / "docs" / "img", ROOT / "paper" / "figures"]
METHODS = ["naive", "wilson", "bonferroni", "holm"]
COLORS = {"vs teacher": "#2471a3", "vs gold": "#c0392b"}


def load(name: str) -> list[dict[str, object]]:
    return list(json.loads((ROOT / "results" / name).read_text(encoding="utf-8")))


def save(fig: plt.Figure, name: str) -> None:
    for d in OUTS:
        d.mkdir(parents=True, exist_ok=True)
        fig.savefig(d / f"{name}.png", dpi=150, bbox_inches="tight")
        fig.savefig(d / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_exp1b() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, (variant, title) in zip(
        axes,
        [
            ("distilled", "student trained on the LLM's labels"),
            ("goldtrained", "student trained on gold labels"),
        ],
        strict=True,
    ):
        n = f"exp1b_{variant}_banking77_alpha010"
        t, g = load(f"{n}_vs_teacher.json"), load(f"{n}_vs_gold.json")
        rows = {r["method"]: (r, h) for r, h in zip(t, g, strict=True) if r["m"] == 400}
        x = np.arange(len(METHODS))
        ax.bar(
            x - 0.2,
            [rows[m][0]["violation_rate_all"] for m in METHODS],
            0.4,
            label="target = agree with teacher",
            color=COLORS["vs teacher"],
        )
        ax.bar(
            x + 0.2,
            [rows[m][1]["violation_rate_all"] for m in METHODS],
            0.4,
            label="target = correct (gold label)",
            color=COLORS["vs gold"],
        )
        ax.axhline(0.10, color="k", ls="-.", lw=1, label="allowed failure rate (delta = 0.10)")
        ax.set_xticks(x, METHODS)
        ax.set_title(title, fontsize=10)
        ax.set_ylim(0, 1.05)
    axes[0].set_ylabel("share of draws missing the target")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=8, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.08))
    fig.suptitle(
        "Banking77, Claude Haiku 5.5 as teacher (76.5% correct), risk target 0.10, "
        "400 calibration labels",
        fontsize=10,
        y=1.03,
    )
    save(fig, "fig5_teacher_noise")


def fig_exp2() -> None:
    fig, ax = plt.subplots(figsize=(8, 3.8))
    shifts = ["prior", "perturbed", "unseen"]
    pols = [("static_holm", "#7f8c8d"), ("rolling_naive", "#c0392b"), ("rolling_holm", "#1e8449")]
    rows = [r for r in load("exp2_banking77_w1000.json") if r["audit_rate"] == 0.10]
    x = np.arange(len(shifts))
    for i, (pol, color) in enumerate(pols):
        vals = [
            next(r for r in rows if r["policy"] == pol and r["pool"].endswith(s))[
                "post_block_violation_rate"
            ]
            for s in shifts
        ]
        ax.bar(x + (i - 1) * 0.27, vals, 0.27, label=pol.replace("_", " "), color=color)
    ax.set_xticks(x, ["class-prior shift", "word noise", "unseen classes"])
    ax.set_ylabel("share of post-shift blocks above the risk target")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=8)
    ax.set_title(
        "Banking77 drift streams, 10% audit rate, 1,000-label window, risk target 0.05", fontsize=10
    )
    save(fig, "fig6_drift_policies")


if __name__ == "__main__":
    fig_exp1b()
    fig_exp2()
    print("wrote fig5_teacher_noise, fig6_drift_policies")
