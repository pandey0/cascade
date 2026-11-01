"""Break-even table from measured teacher cost/call (cached Claude Haiku 5.5 run).

Coverage values are illustrative operating points. Writes results/economics.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cascade.economics import break_even_volume  # noqa: E402


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
    (ROOT / "results" / "economics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:9]))


if __name__ == "__main__":
    main()
