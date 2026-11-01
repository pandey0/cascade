#!/usr/bin/env bash
# Headless-browser screenshots of LOCAL pages only (never the desktop): Grafana dashboard with live
# data and the gateway's Swagger UI. Needs Docker (grafana, prometheus images), Chrome, cached
# embeddings. Output: docs/img/{grafana_dashboard,swagger_ui}.png (copied to evidence/screenshots/).
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv/bin/activate
S=$(mktemp -d)
# KEEP_UP=1: leave the stack running (for taking screenshots in a real browser); tear down with
#   docker rm -f prom-shot grafana-shot; kill $(cat /tmp/cascade_shot.pid); rm -rf <tmpdir printed below>
[ -z "${KEEP_UP:-}" ] && trap 'docker rm -f prom-shot grafana-shot > /dev/null 2>&1 || true; [ -n "${SPID:-}" ] && kill "$SPID" 2>/dev/null || true; rm -rf "$S"' EXIT
CHROME=${CHROME:-$(command -v google-chrome || command -v chromium || echo /opt/google/chrome/chrome)}
mkdir -p "$S/prom" "$S/prov/datasources" "$S/prov/dashboards" "$S/dash" docs/img evidence/screenshots
sed 's/gateway:8080/127.0.0.1:8083/; s/scrape_interval: 15s/scrape_interval: 5s/; s/evaluation_interval: 15s/evaluation_interval: 5s/' ops/prometheus/prometheus.yml > "$S/prom/prometheus.yml"
cp ops/prometheus/alerts.yml "$S/prom/"; cp ops/grafana/cascade-dashboard.json "$S/dash/"
printf 'apiVersion: 1\ndatasources:\n  - {name: Prometheus, uid: prom-main, type: prometheus, access: proxy, url: "http://127.0.0.1:9099", isDefault: true}\n' > "$S/prov/datasources/ds.yml"
printf 'apiVersion: 1\nproviders:\n  - {name: cascade, type: file, options: {path: /var/lib/grafana/dashboards}}\n' > "$S/prov/dashboards/d.yml"
rm -f data/cache/demo_audit.db*
CASCADE_ALLOW_ANONYMOUS=1 CASCADE_RATE_LIMIT_PER_MIN=100000 python scripts/serve_demo.py --port 8083 --audit-rate 0.3 > evidence/logs/screenshots_server.log 2>&1 &
SPID=$!
echo "$SPID" > /tmp/cascade_shot.pid
for _ in $(seq 1 90); do curl -sf localhost:8083/healthz > /dev/null && break; sleep 1; done
docker run -d --name prom-shot --network host -v "$S/prom:/etc/prometheus:ro" prom/prometheus:v2.55.1 --config.file=/etc/prometheus/prometheus.yml --web.listen-address=127.0.0.1:9099 > /dev/null
docker run -d --name grafana-shot --network host -e GF_SERVER_HTTP_ADDR=127.0.0.1 -e GF_SERVER_HTTP_PORT=3009 -e GF_AUTH_ANONYMOUS_ENABLED=true -e GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer -e GF_ANALYTICS_REPORTING_ENABLED=false -e GF_ANALYTICS_CHECK_FOR_UPDATES=false -v "$S/prov:/etc/grafana/provisioning:ro" -v "$S/dash:/var/lib/grafana/dashboards:ro" grafana/grafana:11.3.0 > /dev/null
for _ in $(seq 1 60); do curl -sf localhost:3009/api/health > /dev/null && break; sleep 2; done
# traffic with a mix of paths and a few errors so every panel has data
python scripts/loadtest.py --url http://127.0.0.1:8083 --concurrency 6 --seconds 45 --label screenshots > /dev/null 2>&1 &
sleep 5
python - << 'PY'
import json, time, urllib.error, urllib.request
for _ in range(25):
    r = urllib.request.Request("http://127.0.0.1:8083/v1/decide", data=json.dumps({"decision": "banking77", "input": "x" * 5000}).encode(), headers={"content-type": "application/json"})
    try: urllib.request.urlopen(r)
    except urllib.error.HTTPError: pass
    time.sleep(0.5)
PY
wait %3 2> /dev/null || sleep 30
sleep 12
if [ -n "${KEEP_UP:-}" ]; then echo "stack up (tmpdir $S): grafana http://127.0.0.1:3009  gateway http://127.0.0.1:8083"; exit 0; fi
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --window-size=1500,1000 --timeout=40000 \
  --screenshot=docs/img/grafana_dashboard.png "http://127.0.0.1:3009/d/cascade-gw/cascade-gateway?orgId=1&kiosk&from=now-10m&to=now&refresh=off" 2> /dev/null
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --window-size=1300,1100 --virtual-time-budget=20000 \
  --screenshot=docs/img/swagger_ui.png "http://127.0.0.1:8083/docs" 2> /dev/null
cp docs/img/grafana_dashboard.png docs/img/swagger_ui.png evidence/screenshots/
ls -la docs/img/*.png
