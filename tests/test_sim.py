import numpy as np
import pytest

from cascade.gates import default_grid
from cascade.sim import SynthModel, run_exp0, to_markdown


def test_true_curves_are_monotone_and_sane() -> None:
    cov, risk = SynthModel().true_curves(default_grid(steps=51))
    assert cov[0] == pytest.approx(1.0)
    assert np.all(np.diff(cov) <= 1e-12)
    finite = risk[~np.isnan(risk)]
    assert np.all(np.diff(finite) <= 1e-9)  # risk falls as threshold rises


@pytest.mark.slow
def test_certified_respects_delta_and_naive_is_worse() -> None:
    rows = run_exp0([300], trials=400, alpha=0.05, delta=0.1, seed=3)
    by = {r["method"]: r for r in rows}
    for name in ("strict_sequence", "bonferroni", "holm", "split_sequence"):
        assert by[name]["violation_rate_all"] <= 0.1 + 0.04, name
    assert by["naive"]["violation_rate_all"] > by["strict_sequence"]["violation_rate_all"]
    assert by["wilson"]["violation_rate_all"] < by["naive"]["violation_rate_all"]
    assert "holm" in to_markdown(rows, 0.05, 0.1)
