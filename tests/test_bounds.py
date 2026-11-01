import numpy as np
import pytest

from cascade.bounds import cp_lower, cp_upper


def test_upper_matches_closed_form_for_zero_errors() -> None:
    # k = 0: upper = 1 - delta**(1/n)
    assert cp_upper(0, 10, 0.05) == pytest.approx(1 - 0.05 ** (1 / 10), rel=1e-9)


def test_lower_matches_closed_form_for_all_successes() -> None:
    assert cp_lower(10, 10, 0.05) == pytest.approx(0.05 ** (1 / 10), rel=1e-9)


def test_vacuous_cases() -> None:
    assert cp_upper(0, 0, 0.1) == 1.0
    assert cp_upper(5, 5, 0.1) == 1.0
    assert cp_lower(0, 10, 0.1) == 0.0


def test_upper_bound_is_monotone_in_errors_and_n() -> None:
    assert cp_upper(1, 100, 0.1) < cp_upper(5, 100, 0.1)
    assert cp_upper(1, 1000, 0.1) < cp_upper(1, 100, 0.1)


@pytest.mark.parametrize("bad", [(-1, 5, 0.1), (6, 5, 0.1), (1, 5, 0.0), (1, 5, 1.0)])
def test_invalid_inputs_raise(bad: tuple[int, int, float]) -> None:
    with pytest.raises(ValueError, match=r"need|delta"):
        cp_upper(*bad)


@pytest.mark.slow
def test_upper_bound_coverage_is_at_least_nominal() -> None:
    rng = np.random.default_rng(1)
    p, n, delta, trials = 0.07, 200, 0.1, 6000
    k = rng.binomial(n, p, size=trials)
    covered = np.mean([cp_upper(int(x), n, delta) >= p for x in k])
    assert covered >= 1 - delta - 0.01  # Clopper-Pearson is conservative
