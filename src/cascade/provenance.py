"""Run provenance: manifests and an experiment ledger, so every number can be traced.

A manifest records the command, timing, code state (git commit if any, plus a hash of the source
tree so uncommitted work is still pinned), environment and the checksums of input and output
files. The ledger is a CSV with one line per recorded run.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from collections.abc import Iterable
from importlib import metadata
from pathlib import Path
from typing import Any

PACKAGES = ("cascade-llm", "numpy", "scipy", "scikit-learn", "pydantic", "sentence-transformers")
LEDGER_FIELDS = ("started_utc", "name", "command", "commit", "source_sha256", "wall_s", "manifest")


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_tree_sha256(root: str | Path) -> str:
    """Hash of tracked-style source files (src/, scripts/, pyproject.toml), order-independent."""
    base = Path(root)
    files = sorted(
        [*base.glob("src/**/*.py"), *base.glob("scripts/**/*.py"), base / "pyproject.toml"]
    )
    digest = hashlib.sha256()
    for f in files:
        if f.is_file():
            digest.update(str(f.relative_to(base)).encode())
            digest.update(f.read_bytes())
    return digest.hexdigest()


def git_state(root: str | Path) -> dict[str, Any]:
    """Current commit and dirty flag (commit is None outside a repo or before the first commit)."""

    def run(*args: str) -> str | None:
        try:
            out = subprocess.run(  # noqa: S603 (fixed argv, no shell, no user input)
                ["git", "-C", str(root), *args],  # noqa: S607
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout.strip()

    commit = run("rev-parse", "HEAD")
    dirty = run("status", "--porcelain")
    return {"commit": commit or None, "dirty": None if dirty is None else bool(dirty)}


def environment() -> dict[str, Any]:
    versions: dict[str, str] = {}
    for name in PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "packages": versions,
    }


def build_manifest(  # noqa: PLR0917
    name: str,
    command: list[str],
    root: str | Path,
    inputs: Iterable[str | Path],
    outputs: Iterable[str | Path],
    started: float,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    finished = time.time()
    return {
        "name": name,
        "command": command,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "wall_s": round(finished - started, 2),
        "code": {**git_state(root), "source_sha256": source_tree_sha256(root)},
        "environment": environment(),
        "inputs": {str(p): file_sha256(p) for p in inputs if Path(p).is_file()},
        "outputs": {str(p): file_sha256(p) for p in outputs if Path(p).is_file()},
        "extra": extra or {},
    }


def record_run(
    manifest: dict[str, Any], manifest_path: str | Path, ledger_path: str | Path
) -> None:
    """Write the manifest JSON and append a line to the ledger CSV (created on first use)."""
    mpath = Path(manifest_path)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    lpath = Path(ledger_path)
    lpath.parent.mkdir(parents=True, exist_ok=True)
    new = not lpath.exists()
    with lpath.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if new:
            writer.writerow(LEDGER_FIELDS)
        writer.writerow(
            [
                manifest["started_utc"],
                manifest["name"],
                " ".join(manifest["command"]),
                manifest["code"]["commit"] or "",
                manifest["code"]["source_sha256"][:16],
                manifest["wall_s"],
                str(mpath),
            ]
        )
