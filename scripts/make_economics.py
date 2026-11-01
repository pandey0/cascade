"""Break-even table from measured teacher cost/call (cached Claude Haiku 5.5 run).

Coverage values are illustrative operating points. Writes results/economics.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cascade.economics import (  # noqa: E402
    break_even_daily_volume,
    break_even_volume,
    payback_days,
)


def main() -> None:
    cache = ROOT / "data" / "cache" / "teacher"
    cost = {}
    for task in ("banking77", "clinc150"):
        rows = [
            json.loads(x)
            for x in (cache / f"teacher_{task}_claude_claude-haiku-5-5_n2000_seed0.jsonl")
            .read_text()
            .splitlines()
        ]
        cost[task] = sum(r["usd"] for r in rows) / len(rows)
    lines = [
        "Break-even decisions V* = (labels*c_T + fixed) / (coverage*(c_T*(1-audit) - c_S)).",
        "c_T measured from the Claude Haiku 5.5 labelling run; c_S = 0 (CPU logistic regression,",
        "not costed); fixed cost = 0 (engineering time excluded).",
        "Coverage values are illustrative operating points.\n",
        "| task | c_T (USD/call) | coverage | audit rate | labels | V* (decisions) |",
        "|---|---|---|---|---|---|",
    ]
    for task, c_t in cost.items():
        for cov in (0.3, 0.6, 0.9):
            for audit in (0.0, 0.05, 0.2):
                v = break_even_volume(cov, c_t, labels=3000, audit_rate=audit)
                lines.append(f"| {task} | {c_t:.6f} | {cov:.1f} | {audit:.2f} | 3000 | {v:,.0f} |")
    lines += [
        "",
        "## With hosting and engineering time (the numbers that decide whether it is worth it)",
        "Assumptions, NOT measurements unless stated: LLM cost per call = measured Banking77",
        "value (no prompt caching) or the same call with prompt caching (measured by a probe: see",
        "evidence/logs/caching_probe.json; steady state: more than one request per 5 minutes);",
        "the small model serves ~50 requests/s per node (measured 30-70 on 4 pinned cores) on",
        "a node assumed to cost $0.15/hour; 2 replicas always on ($7.2/day); 50% of requests",
        "answered cheaply; 5% audited; $10,000 of engineering time to adopt.",
        "",
        "| LLM cost/call | break-even volume (covers hosting) | payback of $10k at 100k/day "
        "| at 1M/day | at 10M/day |",
        "|---|---|---|---|---|",
    ]
    host, student = 2 * 0.15 * 24, 0.15 / 3600 / 50
    probe = ROOT / "evidence" / "logs" / "caching_probe.json"
    ratio = 0.1
    cache_label = "assumed 10x cheaper"
    if probe.exists():
        sm = json.loads(probe.read_text(encoding="utf-8"))["summary"]
        ratio = (
            sm["cache"]["median_usd_per_call_steady_state"]
            / sm["no_cache"]["median_usd_per_call_steady_state"]
        )
        cache_label = f"measured, caching {1 / ratio:.1f}x cheaper"
    for name, c_t in (
        ("measured, no caching", cost["banking77"]),
        (cache_label, cost["banking77"] * ratio),
    ):
        be = break_even_daily_volume(0.5, c_t, student, 0.05, host)
        pays = [
            payback_days(v, 0.5, c_t, 10_000, student, 0.05, host)
            for v in (100_000, 1_000_000, 10_000_000)
        ]
        fmt = lambda d: "never" if d == float("inf") else f"{d:,.0f} days"  # noqa: E731
        cells = " | ".join(fmt(d) for d in pays)
        lines.append(f"| ${c_t:.6f} ({name}) | {be:,.0f} requests/day | {cells} |")
    (ROOT / "results" / "economics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:9]))


if __name__ == "__main__":
    main()
