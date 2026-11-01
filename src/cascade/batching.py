"""Micro-batching of embedding calls.

Concurrent requests are queued; one worker thread gathers up to ``max_batch`` of them (waiting at
most ``max_wait_s`` after the first) and runs a single batched call. Transformer encoders do far
more work per second on a batch than on the same items one by one, at the cost of at most
``max_wait_s`` of added latency for the first item in a batch.
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


class MicroBatcher:
    def __init__(
        self,
        batch_fn: Callable[[list[str]], FloatArray],
        max_batch: int = 16,
        max_wait_s: float = 0.005,
    ) -> None:
        if max_batch < 1 or max_wait_s < 0:
            msg = "max_batch must be >= 1 and max_wait_s >= 0"
            raise ValueError(msg)
        self._fn = batch_fn
        self._max_batch = max_batch
        self._max_wait = max_wait_s
        self._q: queue.Queue[tuple[str, Future[FloatArray]] | None] = queue.Queue()
        self.batches: list[int] = []  # sizes of executed batches (for tests and metrics)
        self._thread = threading.Thread(target=self._run, name="micro-batcher", daemon=True)
        self._thread.start()

    def __call__(self, text: str, timeout: float | None = 30.0) -> FloatArray:
        fut: Future[FloatArray] = Future()
        self._q.put((text, fut))
        return fut.result(timeout=timeout)

    def _run(self) -> None:
        while True:
            first = self._q.get()
            if first is None:
                return
            items = [first]
            deadline = time.monotonic() + self._max_wait
            while len(items) < self._max_batch:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    nxt = self._q.get(timeout=remaining)
                except queue.Empty:
                    break
                if nxt is None:
                    self._q.put(None)
                    break
                items.append(nxt)
            self.batches.append(len(items))
            try:
                out = self._fn([t for t, _ in items])
            except Exception as exc:  # propagate to every waiter; keep the worker alive
                for _, fut in items:
                    fut.set_exception(exc)
                continue
            for (_, fut), vec in zip(items, out, strict=True):
                fut.set_result(np.asarray(vec, dtype=np.float64))

    def close(self) -> None:
        self._q.put(None)
        self._thread.join(timeout=5)
