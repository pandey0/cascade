from pathlib import Path

from cascade.quality import check_audit
from cascade.store import AuditStore

LABELS = {"a", "b"}


def _fill(store: AuditStore, n: int, teacher: str = "a", conf: float = 0.9) -> None:
    for i in range(n):
        store.add_audit("d", f"text {i}", conf, "a", teacher, True)


def test_clean_data_passes(tmp_path: Path) -> None:
    s = AuditStore(tmp_path / "a.db")
    _fill(s, 200)
    rep = check_audit(s, "d", LABELS)
    assert rep.ok and rep.rows == 200


def test_too_few_rows_and_bad_labels_and_invalid_rate(tmp_path: Path) -> None:
    s = AuditStore(tmp_path / "a.db")
    _fill(s, 10)
    assert "only 10" in check_audit(s, "d", LABELS).problems[0]
    s2 = AuditStore(tmp_path / "b.db")
    _fill(s2, 150, teacher="__invalid__")
    assert any("invalid" in p for p in check_audit(s2, "d", LABELS).problems)
    s3 = AuditStore(tmp_path / "c.db")
    _fill(s3, 150, teacher="zzz")
    assert any("outside the label set" in p for p in check_audit(s3, "d", LABELS).problems)


def test_out_of_range_confidence_and_duplicates_and_jump(tmp_path: Path) -> None:
    s = AuditStore(tmp_path / "a.db")
    _fill(s, 150, conf=1.7)
    assert any("outside [0, 1]" in p for p in check_audit(s, "d", LABELS).problems)
    d = AuditStore(tmp_path / "d.db")
    for _ in range(150):
        d.add_audit("d", "same text", 0.9, "a", "a", True)
    assert any("duplicate" in p for p in check_audit(d, "d", LABELS).problems)
    j = AuditStore(tmp_path / "j.db")
    _fill(j, 100, teacher="a")  # agrees
    for i in range(100):
        j.add_audit("d", f"late {i}", 0.9, "a", "b", True)  # disagrees
    assert any("moved" in p for p in check_audit(j, "d", LABELS).problems)
