"""SQLite audit store with versioned migrations, retention and online backup.

Stores no raw input text: only a SHA-256 of it (privacy by default). Each row is one audited
decision: the student's confidence and label next to the teacher's label.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

MIGRATIONS: tuple[str, ...] = (
    """CREATE TABLE audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL NOT NULL,
        decision TEXT NOT NULL,
        text_sha256 TEXT NOT NULL,
        confidence REAL NOT NULL,
        student_label TEXT NOT NULL,
        teacher_label TEXT NOT NULL,
        accepted INTEGER NOT NULL
    );
    CREATE INDEX audit_decision_id ON audit (decision, id);""",
    """CREATE TABLE idempotency (
        key TEXT PRIMARY KEY,
        ts REAL NOT NULL,
        response TEXT NOT NULL
    );""",
)
SCHEMA_VERSION = len(MIGRATIONS)


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class AuditStore:
    def __init__(self, path: str | Path) -> None:
        self._conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._lock = threading.Lock()
        self.migrate()

    def migrate(self) -> int:
        with self._lock:
            version = int(self._conn.execute("PRAGMA user_version").fetchone()[0])
            if version > SCHEMA_VERSION:
                msg = f"database schema {version} is newer than this code ({SCHEMA_VERSION})"
                raise RuntimeError(msg)
            for i in range(version, SCHEMA_VERSION):
                self._conn.execute("BEGIN")
                for stmt in filter(None, (s.strip() for s in MIGRATIONS[i].split(";"))):
                    self._conn.execute(stmt)
                self._conn.execute(f"PRAGMA user_version = {i + 1}")
                self._conn.execute("COMMIT")
            return SCHEMA_VERSION

    @property
    def version(self) -> int:
        return int(self._conn.execute("PRAGMA user_version").fetchone()[0])

    def add_audit(  # noqa: PLR0917
        self,
        decision: str,
        text: str,
        confidence: float,
        student_label: str,
        teacher_label: str,
        accepted: bool,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO audit (ts, decision, text_sha256, confidence, student_label, "
                "teacher_label, accepted) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    time.time(),
                    decision,
                    text_hash(text),
                    confidence,
                    student_label,
                    teacher_label,
                    int(accepted),
                ),
            )

    def recent(self, decision: str, n: int) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Last ``n`` audited (confidence, disagreement) pairs for ``decision``, oldest first."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT confidence, student_label != teacher_label FROM audit "
                "WHERE decision = ? ORDER BY id DESC LIMIT ?",
                (decision, n),
            ).fetchall()
        rows.reverse()
        arr = np.array(rows, dtype=np.float64).reshape(-1, 2)
        return arr[:, 0], arr[:, 1]

    def count(self, decision: str) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM audit WHERE decision = ?", (decision,)
            ).fetchone()
        return int(row[0])

    def get_idempotent(self, key: str) -> dict[str, object] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT response FROM idempotency WHERE key = ?", (key,)
            ).fetchone()
        return None if row is None else dict(json.loads(row[0]))

    def put_idempotent(self, key: str, response: dict[str, object]) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO idempotency (key, ts, response) VALUES (?, ?, ?)",
                (key, time.time(), json.dumps(response)),
            )

    def purge_older_than(self, seconds: float) -> int:
        """Retention: delete audit rows and idempotency keys older than ``seconds``."""
        cutoff = time.time() - seconds
        with self._lock:
            a = self._conn.execute("DELETE FROM audit WHERE ts < ?", (cutoff,)).rowcount
            b = self._conn.execute("DELETE FROM idempotency WHERE ts < ?", (cutoff,)).rowcount
        return int(a + b)

    def backup(self, dest: str | Path) -> None:
        """Consistent online backup (safe while serving)."""
        target = sqlite3.connect(str(dest))
        try:
            with self._lock:
                self._conn.backup(target)
        finally:
            target.close()

    def integrity_ok(self) -> bool:
        with self._lock:
            return str(self._conn.execute("PRAGMA integrity_check").fetchone()[0]) == "ok"

    def close(self) -> None:
        with self._lock:
            self._conn.close()
