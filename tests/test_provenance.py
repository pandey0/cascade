import csv
import json
import time
from pathlib import Path

from cascade.cli import main
from cascade.provenance import (
    build_manifest,
    file_sha256,
    git_state,
    record_run,
    source_tree_sha256,
)


def test_hashes_are_stable_and_sensitive(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x = 1\n")
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    first = source_tree_sha256(tmp_path)
    assert first == source_tree_sha256(tmp_path)
    (tmp_path / "src" / "a.py").write_text("x = 2\n")
    assert first != source_tree_sha256(tmp_path)
    f = tmp_path / "f.txt"
    f.write_text("hello")
    assert file_sha256(f) == file_sha256(f) and len(file_sha256(f)) == 64


def test_git_state_outside_a_repo_is_none(tmp_path: Path) -> None:
    state = git_state(tmp_path)
    assert state["commit"] is None


def test_manifest_and_ledger_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "o.json"
    out.write_text("{}")
    m = build_manifest("t", ["cascade", "x"], tmp_path, [], [out], time.time() - 1, {"k": 1})
    assert m["outputs"][str(out)] == file_sha256(out)
    assert m["environment"]["python"] and m["code"]["source_sha256"]
    mp, lp = tmp_path / "m.json", tmp_path / "ledger.csv"
    record_run(m, mp, lp)
    record_run(m, mp, lp)
    assert json.loads(mp.read_text())["name"] == "t"
    rows = list(csv.reader(lp.open()))
    assert rows[0][0] == "started_utc" and len(rows) == 3  # header + 2 appended runs


def test_cli_experiment_writes_manifest_and_ledger(tmp_path: Path) -> None:
    ev = tmp_path / "ev"
    code = main(
        [
            "exp0",
            "--trials",
            "3",
            "--m",
            "100",
            "--out",
            str(tmp_path / "r"),
            "--evidence",
            str(ev),
            "--name",
            "smoke",
        ]
    )
    assert code == 0
    manifest = json.loads((ev / "manifests" / "smoke.manifest.json").read_text())
    assert manifest["extra"]["alpha"] == 0.05
    assert len(list(csv.reader((ev / "ledger.csv").open()))) == 2  # header + one run
