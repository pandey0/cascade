# Runbook

All commands assume the repo root and the project venv. Ports: gateway 8080.

## Quick checks
`curl localhost:8080/healthz` (liveness), `/readyz` (503 if no decisions loaded or the audit DB fails
its integrity check), `/metrics` (Prometheus), `GET /v1/status/<decision>` (needs `X-API-Key`).

## Teacher unavailable or overload
Symptoms: alert `CascadeErrorBudget*`; `cascade_errors_total{kind="teacher_unavailable"|"overloaded"}`.
1. Check the provider status page and your quota. 2. `fail_open=true` (default) keeps serving
the student's best guess as path `cheap_degraded`; if accuracy matters more than availability set
`fail_open=false` (requests then get 503 + Retry-After 5). 3. For overload (503, Retry-After 1)
raise `CASCADE_MAX_CONCURRENCY` or add replicas; do not raise it beyond what the encoder can serve.

## Drift alarm
Symptom: `CascadeRiskMonitorAlarm` (`cascade_drift_alarm == 1`, `cascade_risk_lower_bound > alpha`).
1. `GET /v1/status/<decision>`: confirm `audits` is large enough to trust it. 2. Trigger
`POST /v1/recalibrate/<decision>`; the gate re-certifies on the latest audited window or withdraws.
3. If the gate withdraws, traffic escalates to the teacher (cost up, accuracy safe). 4. Collect the
audited disagreements, retrain the student offline, redeploy, and re-run the benchmark gates.
Expected lag: recovery takes about `window_labels / audit_rate` decisions (docs/notes/exp2-findings.md).

## Audits dropped
Symptom: alert `CascadeAuditsDropping` (`cascade_audits_dropped` increasing), `cascade_audit_queue_depth` near its limit,
`/v1/status/<decision>` shows `audits_dropped` growing. Meaning: audits are labelled by the teacher on background
workers; when the teacher is slow the queue fills and new audits are dropped (counted, never silently lost). Requests are
unaffected; the cost is that re-tuning and the drift monitor see fewer labels. Actions: check the teacher's latency and
errors first; if the teacher is healthy raise `audit_workers` or `audit_queue_size` in the artifact settings; if the audit
rate is higher than the teacher can serve, lower `audit_rate`. Dropping does not bias the sample: the drop depends on load,
not on the request's content.

## Gate withdrawn
Symptom: `cascade_threshold == -1` for 30 min. Cause: too few audit labels, or no threshold has a
certifiable risk. Raise `audit_rate`, widen `window_labels`, relax `alpha`, or retrain the student.

## Latency
Check `cascade_decide_seconds` by path. The cheap path is dominated by the encoder; see
`docs/perf.md` (micro-batching) before adding replicas. Teacher path latency is the provider's.

## Backup and restore of the audit store
Backup (online, safe while serving): `python -c "from cascade.store import AuditStore; AuditStore('audit.db').backup('audit.bak')"`.
Restore: stop the gateway, copy the backup over `audit.db` (and remove `-wal`/`-shm`), start; the
store re-checks its schema version and `/readyz` runs `PRAGMA integrity_check`. Tested in `tests/test_store.py`.

## Rollback
Deploy by image tag; roll back by redeploying the previous tag. The audit DB schema is versioned
and refuses to open if it is newer than the code, so roll back code and data together
(restore the pre-upgrade backup).
