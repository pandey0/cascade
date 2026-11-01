import threading
import time
from concurrent.futures import TimeoutError as FutTimeout

import numpy as np
import pytest
from numpy.typing import NDArray

from cascade.batching import MicroBatcher


def _fn(texts: list[str]) -> NDArray[np.float64]:
    return np.array([[float(len(t)), 1.0] for t in texts])


def test_single_call_returns_its_own_vector() -> None:
    b = MicroBatcher(_fn, max_batch=4, max_wait_s=0.0)
    assert b("abc").tolist() == [3.0, 1.0]
    b.close()


def test_concurrent_calls_are_batched_and_routed_correctly() -> None:
    def slow(texts: list[str]) -> NDArray[np.float64]:
        time.sleep(0.05)
        return _fn(texts)

    b = MicroBatcher(slow, max_batch=8, max_wait_s=0.05)
    results: dict[int, float] = {}

    def call(i: int) -> None:
        results[i] = float(b("x" * (i + 1))[0])

    ts = [threading.Thread(target=call, args=(i,)) for i in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    b.close()
    assert results == {i: float(i + 1) for i in range(8)}
    assert max(b.batches) > 1 and sum(b.batches) == 8


def test_exception_reaches_all_waiters_and_worker_survives() -> None:
    state = {"fail": True}

    def flaky(texts: list[str]) -> NDArray[np.float64]:
        if state["fail"]:
            msg = "encoder down"
            raise RuntimeError(msg)
        return _fn(texts)

    b = MicroBatcher(flaky, max_batch=2, max_wait_s=0.0)
    with pytest.raises(RuntimeError, match="encoder down"):
        b("a")
    state["fail"] = False
    assert b("ab").tolist() == [2.0, 1.0]
    b.close()


def test_invalid_config_and_timeout() -> None:
    with pytest.raises(ValueError, match="max_batch"):
        MicroBatcher(_fn, max_batch=0)

    def slow(texts: list[str]) -> NDArray[np.float64]:
        time.sleep(0.3)
        return _fn(texts)

    b = MicroBatcher(slow, max_batch=1, max_wait_s=0.0)
    with pytest.raises(FutTimeout):
        b("a", timeout=0.05)
    b.close()
