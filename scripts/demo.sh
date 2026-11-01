#!/usr/bin/env bash
# End-to-end local demo: real student + MiniLM, SIMULATED teacher (300 ms). Prints a transcript.
# Needs cached embeddings (run scripts/run_all.sh once). Port 8083.
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv/bin/activate
rm -f data/cache/demo_audit.db*
CASCADE_API_KEYS=demo-key CASCADE_RATE_LIMIT_PER_MIN=1000 \
  python scripts/serve_demo.py --port 8083 --audit-rate 0.5 > evidence/logs/demo_server.log 2>&1 &
pid=$!; trap 'kill $pid 2>/dev/null || true' EXIT
for _ in $(seq 1 90); do curl -sf localhost:8083/healthz > /dev/null && break; sleep 1; done
post() { curl -s -X POST localhost:8083/v1/decide -H 'content-type: application/json' "$@"; echo; }
# real held-out Banking77 messages (the simulated teacher knows their gold labels)
python - > /tmp/cascade_demo_texts.txt <<'PY'
import os, sys
sys.path.insert(0, "src"); os.environ.setdefault("HF_HOME", "data/cache/hf")
from cascade.data import two_way_split
from cascade.datasets_io import load_task
texts, _, _ = load_task("banking77")
_, po = two_way_split(texts, 0.5, 0)
for i in po[:60]:
    print(texts[i].replace('"', "'"))
PY
mapfile -t T < /tmp/cascade_demo_texts.txt
body() { printf '{"decision":"banking77","input":"%s"}' "$1"; }
echo '$ no key'; post -d "$(body "${T[0]}")"
echo '$ with key: first 6 held-out messages (path shows cheap vs teacher)'
for i in 0 1 2 3 4 5; do
  echo "  ${T[$i]}"; post -H 'X-API-Key: demo-key' -d "$(body "${T[$i]}")" | cut -c1-120
done
echo '$ idempotency: same key twice (second is a replay, no second teacher call)'
for _ in 1 2; do curl -s -i -X POST localhost:8083/v1/decide -H 'content-type: application/json' \
  -H 'X-API-Key: demo-key' -H 'Idempotency-Key: demo-1' -d "$(body "${T[6]}")" | grep -i -E "^HTTP|idempotent-replay" ; done
echo '$ oversize input'; python - <<'PY'
import json, urllib.request
req = urllib.request.Request("http://localhost:8083/v1/decide", data=json.dumps({"decision":"banking77","input":"x"*5000}).encode(),
  headers={"content-type":"application/json","X-API-Key":"demo-key"})
try: urllib.request.urlopen(req)
except Exception as e: print(e)
PY
for i in $(seq 7 59); do post -H 'X-API-Key: demo-key' -d "$(body "${T[$i]}")" > /dev/null; done
echo '$ status after 60 requests (audit rate 50%)'
curl -s localhost:8083/v1/status/banking77 -H 'X-API-Key: demo-key'; echo
echo '$ metrics excerpt'; curl -s localhost:8083/metrics | grep -E '^cascade_(decisions_total|threshold|risk_lower_bound|drift_alarm)'
