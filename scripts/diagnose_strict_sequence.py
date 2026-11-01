"""Evidence for ADR 0004: why the strict-start fixed-sequence gate almost never deploys.

For one real calibration draw, list per threshold: items accepted, errors, the Clopper-Pearson
upper bound at delta, and the pool's true risk/coverage. Writes
evidence/diagnostics/strict_sequence_pitfall.csv (consumed by make_figures.py).
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from cascade.bounds import cp_upper
from cascade.gates import default_grid

ROOT = Path(__file__).resolve().parents[1]
DELTA, ALPHA, M, SEED = 0.1, 0.05, 2000, 0


def main() -> None:
    pool = np.load(ROOT / "data/cache/pools_banking77_seed0.npz")
    scores, errors = pool["scores"], pool["errors"]
    idx = np.random.default_rng(SEED).choice(len(scores), M, replace=False)
    s, e = scores[idx], errors[idx]
    rows = []
    for t in default_grid()[::-1]:
        acc = s >= t
        n = int(acc.sum())
        if n == 0:
            continue
        k = int(e[acc].sum())
        pacc = scores >= t
        rows.append(
            {
                "threshold": round(float(t), 4),
                "n_accepted": n,
                "errors": k,
                "cp_upper_bound": round(cp_upper(k, n, DELTA), 5),
                "passes_alpha": cp_upper(k, n, DELTA) <= ALPHA,
                "pool_true_risk": round(float(errors[pacc].mean()), 5),
                "pool_coverage": round(float(pacc.mean()), 4),
            }
        )
    out = ROOT / "evidence/diagnostics/strict_sequence_pitfall.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    first = rows[0]
    print(
        f"strictest non-empty threshold {first['threshold']}: n={first['n_accepted']}, "
        f"errors={first['errors']}, CP upper bound {first['cp_upper_bound']} > alpha {ALPHA}: "
        f"the strict-start walk stops here. wrote {out}"
    )


if __name__ == "__main__":
    main()
