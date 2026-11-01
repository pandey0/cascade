"""Teacher abstraction: any callable returning a labelled, costed response, with a disk cache."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class TeacherResponse:
    label: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float


class BudgetExceededError(RuntimeError):
    """Raised before a teacher call that would exceed the configured spend cap."""


class CachedTeacher:
    """Wrap a teacher with a SQLite cache keyed by (model, prompt version, input).

    Cached calls cost nothing and are counted separately, so experiments are reproducible
    and re-runs never re-bill. ``max_usd`` is a hard cap on *new* spend in this process.
    """

    def __init__(
        self,
        inner: Callable[[str], TeacherResponse],
        cache_path: str | Path,
        model_id: str,
        prompt_version: str = "v1",
        max_usd: float | None = None,
    ) -> None:
        self._inner = inner
        self._model_id = model_id
        self._prompt_version = prompt_version
        self._max_usd = max_usd
        self._db = sqlite3.connect(str(cache_path))
        self._db.execute("CREATE TABLE IF NOT EXISTS t (k TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.hits = 0
        self.misses = 0
        self.spent_usd = 0.0

    def _key(self, text: str) -> str:
        raw = f"{self._model_id}\x1f{self._prompt_version}\x1f{text}".encode()
        return hashlib.sha256(raw).hexdigest()

    def __call__(self, text: str) -> TeacherResponse:
        key = self._key(text)
        row = self._db.execute("SELECT payload FROM t WHERE k = ?", (key,)).fetchone()
        if row is not None:
            self.hits += 1
            return TeacherResponse(**json.loads(row[0]))
        if self._max_usd is not None and self.spent_usd >= self._max_usd:
            msg = f"teacher spend cap reached: {self.spent_usd:.4f} >= {self._max_usd:.4f} USD"
            raise BudgetExceededError(msg)
        resp = self._inner(text)
        self.misses += 1
        self.spent_usd += resp.cost_usd
        self._db.execute(
            "INSERT INTO t (k, payload) VALUES (?, ?)", (key, json.dumps(asdict(resp)))
        )
        self._db.commit()
        return resp

    def close(self) -> None:
        self._db.close()
