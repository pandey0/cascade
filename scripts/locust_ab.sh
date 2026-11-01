#!/usr/bin/env bash
# Locust A/B: default vs micro-batching, server on cores 0-3, Locust on cores 4-5, CPU/RSS sampled.
# Simulated 300 ms teacher; shared desktop: relative numbers only. REPS=3 by default.
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv/bin/activate
OUT=evidence/logs/locust_ab; mkdir -p "$OUT"
for rep in $(seq 1 "${REPS:-3}"); do
  for cfg in "baseline:0" "batch16:16"; do
    name=${cfg%%:*}; batch=${cfg##*:}
    rm -f data/cache/demo_audit.db*
    CASCADE_ALLOW_ANONYMOUS=1 CASCADE_RATE_LIMIT_PER_MIN=10000000 CASCADE_MAX_CONCURRENCY=64 \
      taskset -c 0-3 python scripts/serve_demo.py --port 8082 --batch "$batch" > "$OUT/server_${name}.log" 2>&1 &
    pid=$!
    for _ in $(seq 1 90); do curl -sf http://127.0.0.1:8082/healthz > /dev/null && break; sleep 1; done
    python scripts/sample_proc.py "$pid" "$OUT/${name}_rep${rep}_proc.csv" &
    spid=$!
    taskset -c 4-5 locust -f scripts/locustfile.py --headless -u 24 -r 24 -t 30s --host http://127.0.0.1:8082 \
      --csv "$OUT/${name}_rep${rep}" --only-summary > "$OUT/${name}_rep${rep}.log" 2>&1 || true
    kill "$spid" 2> /dev/null || true; kill "$pid"; wait "$pid" 2> /dev/null || true
  done
done
echo DONE
