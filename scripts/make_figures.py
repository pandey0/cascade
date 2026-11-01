"""Generate paper figures and LaTeX tables from result files (no hand-typed numbers)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import ScalarFormatter

from cascade.metrics import risk_coverage
from cascade.provenance import file_sha256

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "paper/figures"
TAB = ROOT / "paper/tables"
SETTINGS = [
    ("Banking77, risk target 0.05", "exp1a_banking77_alpha005"),
    ("Banking77, risk target 0.03", "exp1a_banking77_alpha003"),
    ("CLINC150, risk target 0.02", "exp1a_clinc150_alpha002"),
]
STYLE = {
    "naive": ("#c0392b", "-"),
    "safety80": ("#e67e22", "--"),
    "wilson": ("#f1c40f", "--"),
    "certify_once": ("#7f8c8d", "-"),
    "strict_sequence": ("#95a5a6", ":"),
    "bonferroni": ("#2471a3", "-"),
    "holm": ("#1e8449", "--"),
    "split_sequence": ("#8e44ad", "-"),
}
DELTA = 0.10
sources: list[Path] = []


def load(name: str) -> list[dict]:
    path = ROOT / "results" / f"{name}.json"
    sources.append(path)
    return json.loads(path.read_text())


def series(
    rows: list[dict], method: str, key: str
) -> tuple[list[int], np.ndarray, np.ndarray, np.ndarray]:
    sel = sorted((r for r in rows if r["method"] == method), key=lambda r: r["m"])
    return (
        [r["m"] for r in sel],
        np.array([r[key] for r in sel]),
        np.array([r[key + "_min"] for r in sel]),
        np.array([r[key + "_max"] for r in sel]),
    )


def metric_figure(key: str, ylabel: str, fname: str, hline: float | None) -> None:
    fig, axes = plt.subplots(1, len(SETTINGS), figsize=(14, 3.8), sharey=True)
    for ax, (title, name) in zip(axes, SETTINGS, strict=True):
        rows = load(name)
        for method, (colour, ls) in STYLE.items():
            m, mean, lo, hi = series(rows, method, key)
            marker = "x" if method == "holm" else "o"
            ax.plot(m, mean, color=colour, ls=ls, marker=marker, ms=4, lw=1.4, label=method)
            ax.fill_between(m, lo, hi, color=colour, alpha=0.12)
        if hline is not None:
            ax.axhline(hline, color="black", lw=0.8, ls="-.")
        ax.set_xscale("log")
        ax.set_xticks([250, 500, 1000, 2000])
        ax.get_xaxis().set_major_formatter(ScalarFormatter())
        ax.minorticks_off()
        ax.set_xlabel("calibration examples (m)")
        ax.set_title(title, fontsize=10)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel(ylabel)
    axes[-1].legend(fontsize=7, loc="center left", bbox_to_anchor=(1.01, 0.5))
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{fname}.{ext}", dpi=170, bbox_inches="tight")
    plt.close(fig)


def risk_coverage_figure() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    grid = np.linspace(0.0, 1.0, 401)
    for ax, (task, alphas) in zip(
        axes, (("banking77", (0.05, 0.03)), ("clinc150", (0.02,))), strict=True
    ):
        for seed in range(5):
            path = ROOT / f"data/cache/pools_{task}_seed{seed}.npz"
            if not path.exists():
                continue
            sources.append(path)
            d = np.load(path)
            cov, risk = risk_coverage(d["scores"], d["errors"], grid)
            ax.plot(cov, risk, lw=1, alpha=0.7, label=f"split {seed}")
        for a in alphas:
            ax.axhline(a, color="black", lw=0.7, ls="-.")
        ax.set_xlabel("coverage")
        ax.set_ylabel("risk (error among accepted)")
        ax.set_title(f"{task}: student risk-coverage (pool)", fontsize=10)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"fig3_risk_coverage.{ext}", dpi=170, bbox_inches="tight")
    plt.close(fig)


def pitfall_figure() -> None:
    path = ROOT / "evidence/diagnostics/strict_sequence_pitfall.csv"
    if not path.exists():
        return
    sources.append(path)
    rows = list(csv.DictReader(path.open()))
    t = np.array([float(r["threshold"]) for r in rows])
    n = np.array([int(r["n_accepted"]) for r in rows])
    ub = np.array([float(r["cp_upper_bound"]) for r in rows])
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    ax.plot(t, ub, color="#2471a3", label="Clopper-Pearson upper bound (delta=0.1)")
    ax.axhline(0.05, color="black", ls="-.", lw=0.8, label="risk target 0.05")
    ax.set_xlabel("confidence threshold (strict at left, lenient at right)")
    ax.set_ylabel("upper bound on risk")
    ax.invert_xaxis()
    ax.set_ylim(0, 0.2)
    ax2 = ax.twinx()
    ax2.plot(t, n, color="#c0392b", ls=":", label="items accepted")
    ax2.set_ylabel("items accepted")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper left")
    ax.set_title("Strict-start fixed sequence stops at the first tiny-sample threshold", fontsize=9)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"fig4_strict_sequence_pitfall.{ext}", dpi=170, bbox_inches="tight")
    plt.close(fig)


def latex_table() -> None:
    rows_out = []
    for title, name in SETTINGS:
        rows = load(name)
        for m in (1000, 2000):
            for method in ("naive", "wilson", "bonferroni", "holm"):
                r = next(x for x in rows if x["m"] == m and x["method"] == method)
                rows_out.append(
                    f"{title.split(',')[0]} & {title.split('risk target ')[1]} & {m} & "
                    f"{method.replace('_', ' ')} & {r['violation_rate_all']:.3f} & "
                    f"{r['mean_coverage']:.3f} & {r['deploy_rate']:.2f} \\\\"
                )
    header = (
        "\\begin{tabular}{llrlrrr}\n\\toprule\nTask & $\\alpha$ & $m$ & Method & "
        "Violation & Coverage & Deploy \\\\\n\\midrule\n"
    )
    (TAB / "main_results.tex").write_text(
        header + "\n".join(rows_out) + "\n\\bottomrule\n\\end{tabular}\n"
    )


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    metric_figure("violation_rate_all", "violation rate", "fig1_violation_vs_m", DELTA)
    metric_figure("mean_coverage", "mean coverage (0 if not deployed)", "fig2_coverage_vs_m", None)
    risk_coverage_figure()
    pitfall_figure()
    latex_table()
    lines = [
        "# Figure and table provenance (generated by scripts/make_figures.py)\n",
        "| source file | sha256 |",
        "|---|---|",
    ]
    for p in sorted(set(sources)):
        lines.append(f"| `{p.relative_to(ROOT)}` | `{file_sha256(p)[:16]}` |")
    (FIG / "PROVENANCE.md").write_text("\n".join(lines) + "\n")
    print("figures:", sorted(x.name for x in FIG.glob("*.png")))


if __name__ == "__main__":
    main()
