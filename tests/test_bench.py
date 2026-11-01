import json
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from cascade.bench import aggregate_pools, run_pool_experiment, to_markdown_ranges
from cascade.cli import main
from cascade.data import two_way_split
from cascade.sim import METHODS, SynthModel


def _pool(n: int = 4000) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    return SynthModel().sample(n, np.random.default_rng(0))


def test_pool_experiment_runs_and_reports_all_methods() -> None:
    s, e = _pool()
    rows = run_pool_experiment(s, e, [200], trials=20, alpha=0.1, delta=0.1, seed=1)
    assert {r["method"] for r in rows} == set(METHODS)
    assert all(r["m"] == 200 for r in rows)


def test_pool_experiment_rejects_oversized_calibration() -> None:
    s, e = _pool(100)
    with pytest.raises(ValueError, match="exceeds half"):
        run_pool_experiment(s, e, [80], trials=2, alpha=0.1, delta=0.1)


def test_two_way_split_keeps_duplicates_together() -> None:
    texts = [f"q{i % 25}" for i in range(250)]
    a, b = two_way_split(texts, 0.5, seed=2)
    assert not ({texts[i] for i in a} & {texts[i] for i in b})
    assert len(a) + len(b) == 250
    with pytest.raises(ValueError, match="first_fraction"):
        two_way_split(texts, 1.5)


def test_cli_exp1a_on_cached_pool(tmp_path: Path) -> None:
    s, e = _pool(3000)
    np.savez(tmp_path / "p.npz", scores=s, errors=e)
    out = tmp_path / "out"
    assert (
        main(
            [
                "exp1a",
                str(tmp_path / "p.npz"),
                "--m",
                "200",
                "--trials",
                "10",
                "--out",
                str(out),
                "--evidence",
                str(tmp_path / "ev"),
            ]
        )
        == 0
    )
    assert json.loads((out / "exp1a.json").read_text())[0]["pools"] == 1


def test_aggregate_and_markdown_ranges() -> None:
    s, e = _pool(3000)
    a = run_pool_experiment(s, e, [200], trials=15, alpha=0.1, delta=0.1, seed=1)
    b = run_pool_experiment(s, e, [200], trials=15, alpha=0.1, delta=0.1, seed=2)
    rows = aggregate_pools([a, b])
    r = rows[0]
    assert r["pools"] == 2
    assert r["violation_rate_all_min"] <= r["violation_rate_all"] <= r["violation_rate_all_max"]
    md = to_markdown_ranges(rows, 0.1, 0.1)
    assert "min-max across splits" in md and "holm" in md
