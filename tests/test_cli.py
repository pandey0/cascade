import json
from pathlib import Path

from cascade.cli import main
from cascade.sim import METHODS


def test_version(capsys: object) -> None:
    assert main(["version"]) == 0


def test_exp0_writes_outputs(tmp_path: Path) -> None:
    out = tmp_path / "res"
    assert (
        main(
            [
                "exp0",
                "--trials",
                "5",
                "--m",
                "100",
                "--out",
                str(out),
                "--evidence",
                str(tmp_path / "ev"),
            ]
        )
        == 0
    )
    rows = json.loads((out / "exp0.json").read_text())
    assert {r["method"] for r in rows} == set(METHODS)
    assert (out / "exp0.md").read_text().startswith("Target risk")
