#!/usr/bin/env bash
# Alternating A/B load test (default vs micro-batching) to average out host noise.
# Simulated teacher (300 ms); loadgen and server share one machine: relative numbers only.
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv/bin/activate
OUT=evidence/logs/perf_ab.jsonl
for rep in 1 2 3; do
  for cfg in "baseline:0" "batch16:16"; do
    name=${cfg%%:*}; batch=${cfg##*:}
    rm -f data/cache/demo_audit.db*
    CASCADE_ALLOW_ANONYMOUS=1 CASCADE_RATE_LIMIT_PER_MIN=1000000 CASCADE_MAX_CONCURRENCY=64 \
      python scripts/serve_demo.py --port 8082 --batch "$batch" > "evidence/logs/serve_${name}.log" 2>&1 &
    pid=$!
    for _ in $(seq 1 60); do curl -sf http://127.0.0.1:8082/healthz > /dev/null && break; sleep 1; done
    python scripts/loadtest.py --url http://127.0.0.1:8082 --concurrency 24 --seconds 15 \
      --label "${name}_rep${rep}" --out "$OUT" 2>&1 | grep -v HF
    kill "$pid"; wait "$pid" 2> /dev/null || true
  done
done
echo DONE
