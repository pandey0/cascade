"""Measure Anthropic prompt caching on our classification prompt with a small real probe.

Sends N calls with the label list as a cacheable system block and N identical calls without
caching, then reports the billed token categories from the response usage. Costs well under a
cent. Prices are inputs (USD per million tokens); the cache multipliers are Anthropic's
published ones (write 1.25x, read 0.1x of the input price) and are applied here, not read
from the API. Needs ANTHROPIC_API_KEY (from .env).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("HF_HOME", str(ROOT / "data" / "cache" / "hf"))

import anthropic  # noqa: E402

from cascade.adapters.gemini import build_system_instruction, label_schema  # noqa: E402
from cascade.datasets_io import load_task  # noqa: E402

PRICE_IN, PRICE_OUT, MODEL, N = 0.10, 0.50, "claude-haiku-5-5", 12


def load_env() -> None:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


class Cfg:
    instructions = "Classify the customer message from a banking app into exactly one intent."


def main() -> None:
    load_env()
    texts, _, names = load_task("banking77")
    Cfg.labels = tuple(names)  # type: ignore[attr-defined]
    system_text = build_system_instruction(Cfg)  # type: ignore[arg-type]
    schema = label_schema(Cfg.labels)  # type: ignore[attr-defined]
    schema["additionalProperties"] = False
    client = anthropic.Anthropic(max_retries=3)
    out: dict[str, list[dict[str, float]]] = {"no_cache": [], "cache": []}
    for mode in ("no_cache", "cache"):
        system: object = system_text
        if mode == "cache":
            system = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]
        for i in range(N):
            t0 = time.perf_counter()
            r = client.messages.create(
                model=MODEL,
                max_tokens=64,
                system=system,  # type: ignore[arg-type]
                messages=[{"role": "user", "content": texts[100 + i]}],
                thinking={"type": "disabled"},
                output_config={
                    "effort": "low",
                    "format": {"type": "json_schema", "schema": schema},
                },
            )
            u = r.usage
            rec = {
                "input": u.input_tokens,
                "output": u.output_tokens,
                "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
                "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
                "ms": (time.perf_counter() - t0) * 1000,
            }
            rec["usd"] = (
                (rec["input"] + 1.25 * rec["cache_write"] + 0.10 * rec["cache_read"]) * PRICE_IN
                + rec["output"] * PRICE_OUT
            ) / 1e6
            out[mode].append(rec)
    summary = {}
    for mode, recs in out.items():
        steady = recs[1:] if mode == "cache" else recs
        summary[mode] = {
            "calls": len(recs),
            "median_usd_per_call_steady_state": sorted(r["usd"] for r in steady)[len(steady) // 2],
            "total_usd": sum(r["usd"] for r in recs),
            "first_call": recs[0],
            "last_call": recs[-1],
            "median_ms": sorted(r["ms"] for r in recs)[len(recs) // 2],
        }
    path = ROOT / "evidence" / "logs" / "caching_probe.json"
    path.write_text(
        json.dumps({"model": MODEL, "raw": out, "summary": summary}, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
