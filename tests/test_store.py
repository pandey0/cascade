import sqlite3
from pathlib import Path

import numpy as np
import pytest

from cascade.store import SCHEMA_VERSION, AuditStore, text_hash


def test_migration_is_idempotent_and_versioned(tmp_path: Path) -> None:
    path = tmp_path / "a.db"
    s = AuditStore(path)
    assert s.version == SCHEMA_VERSION
    s.close()
    s2 = AuditStore(path)  # re-open: no re-migration error, same version
    assert s2.version == SCHEMA_VERSION
    s2.close()


def test_refuses_newer_schema(tmp_path: Path) -> None:
    path = tmp_path / "a.db"
    conn = sqlite3.connect(path)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
    conn.close()
    with pytest.raises(RuntimeError, match="newer"):
        AuditStore(path)


def test_audit_roundtrip_stores_hash_not_text(tmp_path: Path) -> None:
    s = AuditStore(tmp_path / "a.db")
    s.add_audit("d", "secret text", 0.9, "a", "a", True)
    s.add_audit("d", "other", 0.4, "a", "b", False)
    conf, err = s.recent("d", 10)
    assert conf.tolist() == [0.9, 0.4] and err.tolist() == [0.0, 1.0]
    raw = sqlite3.connect(tmp_path / "a.db").execute("SELECT text_sha256 FROM audit").fetchall()
    assert (text_hash("secret text"),) in raw
    assert b"secret text" not in (tmp_path / "a.db").read_bytes()
    assert s.count("d") == 2 and s.recent("none", 5)[0].size == 0


def test_idempotency_first_write_wins(tmp_path: Path) -> None:
    s = AuditStore(tmp_path / "a.db")
    s.put_idempotent("k", {"v": 1})
    s.put_idempotent("k", {"v": 2})
    assert s.get_idempotent("k") == {"v": 1} and s.get_idempotent("x") is None


def test_backup_and_restore_preserves_rows(tmp_path: Path) -> None:
    s = AuditStore(tmp_path / "a.db")
    for i in range(50):
        s.add_audit("d", f"t{i}", i / 50, "a", "a" if i % 2 else "b", True)
    s.backup(tmp_path / "b.db")
    s.close()
    restored = AuditStore(tmp_path / "b.db")
    assert restored.integrity_ok() and restored.count("d") == 50
    conf, _ = restored.recent("d", 50)
    assert np.allclose(conf, np.arange(50) / 50)


def test_retention_purges_old_rows(tmp_path: Path) -> None:
    s = AuditStore(tmp_path / "a.db")
    s.add_audit("d", "t", 0.5, "a", "a", True)
    assert s.purge_older_than(3600) == 0
    assert s.purge_older_than(-1) >= 1 and s.count("d") == 0
