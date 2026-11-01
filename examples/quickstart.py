"""Cascade in 30 lines: why picking the 'confident enough' cutoff naively is risky.

A cheap model answers when its confidence is above a cutoff; we want its error rate on those
answers to stay below 5%. We pick the cutoff from an audited sample of
(confidence, was it wrong?) pairs.
Run:  python examples/quickstart.py      (needs only `pip install -e .`)
"""

import numpy as np

from cascade.gates import coarse_grid, select_holm, select_naive

ALPHA, DELTA, N = 0.05, 0.10, 2000  # target error rate, allowed failure chance, audited sample size


def audited_sample(rng):
    """Synthetic student: the less confident it is, the more often it is wrong."""
    conf = rng.uniform(0.2, 1.0, N)
    wrong = (rng.random(N) < 0.25 * (1 - conf)).astype(float)
    return conf, wrong


def true_error_rate(cutoff):
    """Real error rate of answers above `cutoff` (known here because we built the data)."""
    return 0.25 * (1 - (cutoff + 1) / 2)


rng = np.random.default_rng(0)
conf, wrong = audited_sample(rng)
naive = select_naive(conf, wrong, ALPHA, coarse_grid())
safe = select_holm(conf, wrong, ALPHA, DELTA)
print("ONE AUDIT")
print(
    f"  naive    : cutoff {naive.threshold:.2f}, {naive.coverage:.0%} answered cheaply, "
    f"real error rate {true_error_rate(naive.threshold):.1%}"
)
if safe.threshold is None:
    print("  certified: not enough evidence, keeps using the expensive model")
else:
    print(
        f"  certified: cutoff {safe.threshold:.2f}, {safe.coverage:.0%} answered cheaply, "
        f"real error rate {true_error_rate(safe.threshold):.1%}"
    )

runs = {"naive": [0, 0, 0.0], "certified": [0, 0, 0.0]}  # [deployed, missed target, coverage sum]
for _ in range(300):  # repeat the whole audit 300 times with fresh data
    c, w = audited_sample(rng)
    for name, res in (
        ("naive", select_naive(c, w, ALPHA, coarse_grid())),
        ("certified", select_holm(c, w, ALPHA, DELTA)),
    ):
        if res.threshold is not None:
            runs[name][0] += 1
            runs[name][1] += true_error_rate(res.threshold) > ALPHA
            runs[name][2] += res.coverage
print(f"\n300 REPEATED AUDITS (target: error rate <= {ALPHA:.0%})")
for name, (deployed, missed, cov) in runs.items():
    print(
        f"  {name:9}: deployed {deployed / 3:.0f}% of the time, missed the target in "
        f"{missed / max(deployed, 1):.0%} of those, {cov / max(deployed, 1):.0%} answered cheaply"
    )
