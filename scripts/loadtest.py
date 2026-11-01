"""Closed-loop load test with asyncio + httpx (no extra dependencies).

Sends real Banking77 held-out texts to /v1/decide with N concurrent workers for a fixed time and
prints throughput, latency percentiles and the cheap/teacher mix as JSON. Use against
scripts/serve_demo.py (simulated teacher): numbers are NOT production capacity claims.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("HF_HOME", str(ROOT / "data" / "cache" / "hf"))

from cascade.data import two_way_split  # noqa: E402
from cascade.datasets_io import load_task  # noqa: E402


async def worker(  # noqa: PLR0917
    client: httpx.AsyncClient,
    texts: list[str],
    end: float,
    out: list[tuple[float, str]],
    seed: int,
    headers: dict[str, str],
) -> None:
    rng = np.random.default_rng(seed)
    while time.perf_counter() < end:
        text = texts[int(rng.integers(len(texts)))]
        t0 = time.perf_counter()
        try:
            r = await client.post(
                "/v1/decide", json={"decision": "banking77", "input": text}, headers=headers
            )
            tag = r.json().get("path", "?") if r.status_code == 200 else f"http_{r.status_code}"
        except httpx.HTTPError as exc:
            tag = f"err_{type(exc).__name__}"
        out.append((time.perf_counter() - t0, tag))


async def run(url: str, concurrency: int, seconds: float, key: str | None) -> dict[str, object]:
    texts, _, _ = load_task("banking77")
    _, po = two_way_split(texts, 0.5, 0)
    pool = [texts[i] for i in po[:2000]]
    headers = {"X-API-Key": key} if key else {}
    out: list[tuple[float, str]] = []
    async with httpx.AsyncClient(base_url=url, timeout=30.0) as client:
        await client.get("/healthz")
        start = time.perf_counter()
        end = start + seconds
        await asyncio.gather(
            *(worker(client, pool, end, out, i, headers) for i in range(concurrency))
        )
        wall = time.perf_counter() - start
    lat = np.array([d for d, _ in out]) * 1000.0
    mix = Counter(tag for _, tag in out)
    return {
        "concurrency": concurrency,
        "seconds": round(wall, 1),
        "requests": len(out),
        "rps": round(len(out) / wall, 1),
        "p50_ms": round(float(np.percentile(lat, 50)), 1),
        "p95_ms": round(float(np.percentile(lat, 95)), 1),
        "p99_ms": round(float(np.percentile(lat, 99)), 1),
        "mix": dict(mix),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8081")
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--key", default=None)
    ap.add_argument("--label", default="run")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = asyncio.run(run(a.url, a.concurrency, a.seconds, a.key))
    res["label"] = a.label
    print(json.dumps(res))
    if a.out:
        with Path(a.out).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(res) + "\n")


if __name__ == "__main__":
    main()
