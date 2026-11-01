"""Check a running Grafana: dashboard provisioned, every panel query returns data via /api/ds/query.

Usage: GF_URL=http://127.0.0.1:3009 GF_PASSWORD=... python scripts/grafana_check.py
Needs a gateway under recent traffic and Prometheus scraping it (see docs/ops.md).
"""

from __future__ import annotations

import os
import sys
import time

import httpx

URL = os.environ.get("GF_URL", "http://127.0.0.1:3000")
AUTH = ("admin", os.environ["GF_PASSWORD"])
UID = "cascade-gw"


def main() -> int:
    with httpx.Client(base_url=URL, auth=AUTH, timeout=20.0) as c:
        dash = c.get(f"/api/dashboards/uid/{UID}")
        if dash.status_code != 200:
            print(f"FAIL dashboard {UID} not provisioned: HTTP {dash.status_code}")
            return 1
        body = dash.json()["dashboard"]
        print(f"dashboard: {body['title']!r}, {len(body['panels'])} panels")
        ds = c.get("/api/datasources").json()
        print("datasources:", [(d["name"], d["type"], d["isDefault"]) for d in ds])
        now = int(time.time() * 1000)
        failures = 0
        for panel in body["panels"]:
            queries = [
                {
                    "refId": t["refId"],
                    "datasource": {"uid": ds[0]["uid"], "type": "prometheus"},
                    "expr": t["expr"],
                    "range": True,
                    "instant": False,
                    "intervalMs": 15000,
                    "maxDataPoints": 200,
                }
                for t in panel["targets"]
            ]
            r = c.post(
                "/api/ds/query",
                json={"queries": queries, "from": str(now - 600_000), "to": str(now)},
            )
            if r.status_code != 200:
                print(f"FAIL  {panel['title']}: HTTP {r.status_code} {r.text[:120]}")
                failures += 1
                continue
            results = r.json()["results"]
            rows = 0
            err = None
            for ref in results.values():
                err = err or ref.get("error")
                for f in ref.get("frames", []):
                    vals = f["data"]["values"]
                    rows += len(vals[1]) if len(vals) > 1 else 0
            status = "ok  " if rows > 0 and not err else "FAIL"
            failures += status == "FAIL"
            print(f"{status}  {panel['title']}: {len(results)} queries, {rows} points {err or ''}")
        print(
            "RESULT:", "all panels return data" if not failures else f"{failures} panel(s) failed"
        )
        return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
