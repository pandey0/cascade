"""Failure-injection runs against the real gateway process.

Simulated teacher, real student and encoder.

Scenarios (each starts its own server): flaky teacher with fail-open, flaky teacher fail-closed,
total teacher outage, slow teacher past the timeout, and SIGTERM during load (graceful shutdown).
Writes results/chaos.md and evidence/logs/chaos.jsonl. Needs cached embeddings (run_all.sh).
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections import Counter
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("HF_HOME", str(ROOT / "data" / "cache" / "hf"))
PORT = 8090
URL = f"http://127.0.0.1:{PORT}"
SCEN = {
    "flaky30_failopen": ["--teacher-fail-rate", "0.3"],
    "flaky30_failclosed": ["--teacher-fail-rate", "0.3", "--fail-closed"],
    "outage100_failopen": ["--teacher-fail-rate", "1.0"],
    "slow_teacher_timeout": ["--teacher-ms", "3000", "--teacher-timeout-s", "0.5", "--fail-closed"],
    "sigterm_under_load": [],
}


def texts() -> list[str]:
    from cascade.data import two_way_split  # noqa: PLC0415
    from cascade.datasets_io import load_task  # noqa: PLC0415

    t, _, _ = load_task("banking77")
    _, po = two_way_split(t, 0.5, 0)
    return [t[i] for i in po[:400]]


def start(extra: list[str]) -> subprocess.Popen[bytes]:
    env = {**os.environ, "CASCADE_ALLOW_ANONYMOUS": "1", "CASCADE_RATE_LIMIT_PER_MIN": "1000000"}
    log = (ROOT / "evidence" / "logs" / "chaos_server.log").open("ab")
    proc = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            str(ROOT / "scripts" / "serve_demo.py"),
            "--port",
            str(PORT),
            "--audit-rate",
            "0.1",
            "--db",
            str(ROOT / "data" / "cache" / "chaos.db"),
            *extra,
        ],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=log,
    )
    for _ in range(120):
        try:
            if httpx.get(URL + "/healthz", timeout=1).status_code == 200:
                return proc
        except httpx.HTTPError:
            time.sleep(1)
    proc.kill()
    msg = "server did not start"
    raise RuntimeError(msg)


def fire(
    pool: list[str], n: int, workers: int, out: list[str], stop: threading.Event | None = None
) -> None:
    lock = threading.Lock()
    idx = [0]

    def work() -> None:
        with httpx.Client(base_url=URL, timeout=20.0) as c:
            while True:
                with lock:
                    if idx[0] >= n or (stop is not None and stop.is_set()):
                        return
                    i = idx[0]
                    idx[0] += 1
                try:
                    r = c.post(
                        "/v1/decide", json={"decision": "banking77", "input": pool[i % len(pool)]}
                    )
                    tag = (
                        r.json().get("path", "?")
                        if r.status_code == 200
                        else f"http_{r.status_code}"
                    )
                except httpx.HTTPError as exc:
                    tag = f"conn_{type(exc).__name__}"
                with lock:
                    out.append(tag)

    ts = [threading.Thread(target=work) for _ in range(workers)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def run(name: str, pool: list[str]) -> dict[str, object]:
    (ROOT / "data" / "cache" / "chaos.db").unlink(missing_ok=True)
    proc = start(SCEN[name])
    out: list[str] = []
    result: dict[str, object] = {"scenario": name}
    try:
        if name == "sigterm_under_load":
            stop = threading.Event()
            th = threading.Thread(target=fire, args=(pool, 600, 8, out, stop))
            th.start()
            time.sleep(4)
            before = len(out)
            proc.send_signal(signal.SIGTERM)
            t0 = time.time()
            th.join(timeout=60)
            stop.set()
            result["requests_before_sigterm"] = before
            result["exit_code"] = proc.wait(timeout=30)
            result["shutdown_s"] = round(time.time() - t0, 1)
        else:
            fire(pool, 300, 8, out)
            after: list[str] = []
            fire(pool, 20, 2, after)  # still alive?
            result["healthz_after"] = httpx.get(URL + "/healthz", timeout=3).status_code
            result["status_after"] = httpx.get(URL + "/readyz", timeout=3).status_code
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=30)
    result["mix"] = dict(Counter(out))
    result["n"] = len(out)
    return result


def main() -> None:
    pool = texts()
    results = [run(n, pool) for n in SCEN]
    log = ROOT / "evidence" / "logs" / "chaos.jsonl"
    with log.open("a", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps({"ts": time.time(), **r}) + "\n")
    lines = ["| scenario | requests | outcome mix | extra |", "|---|---|---|---|"]
    for r in results:
        extra = {k: v for k, v in r.items() if k not in ("scenario", "mix", "n")}
        lines.append(f"| {r['scenario']} | {r['n']} | {r['mix']} | {extra} |")
    (ROOT / "results" / "chaos.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
