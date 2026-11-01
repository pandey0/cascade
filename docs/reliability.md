# Reliability: controls and failure-injection results

Controls (all tested): per-call teacher timeout; SDK retries with backoff; fail-open (serve the
student's guess, path `cheap_degraded`) or fail-closed (503 + Retry-After); idempotency keys;
per-key rate limit (429); concurrency limit (503 + Retry-After); audit failures never block a cheap
answer; the gate withdraws when nothing certifies; SQLite WAL with integrity check on `/readyz`.
Not built, by design or not yet: a dead-letter queue (the API is synchronous, failed requests are
returned to the caller, not queued), multi-replica rate limits, circuit breaker around the teacher.

## Failure injection against the running gateway (`scripts/chaos.py`, 2026-11-01)
Real Banking77 student + MiniLM, simulated teacher, 8 clients, 300 requests per scenario,
~8% of requests escalate. Raw: `evidence/logs/chaos.jsonl`, table `results/chaos.md`.

| Scenario | Outcome |
|---|---|
| Teacher fails 30%, fail-open | 0 HTTP errors; 7 degraded answers (student guess) of 23 escalations; 277 cheap unaffected; `/healthz` and `/readyz` 200 afterwards |
| Teacher fails 30%, fail-closed | 5 x 503 (the failed escalations), 18 teacher answers, 277 cheap unaffected; server healthy afterwards |
| Teacher down 100%, fail-open | 0 HTTP errors; all 23 escalations degraded; 277 cheap unaffected |
| Teacher slower than the timeout (3 s vs 0.5 s), fail-closed | all 23 escalations returned 503 within the timeout; cheap path unaffected; healthy afterwards |
| SIGTERM during load | server stopped 0.7 s after the signal (uvicorn graceful shutdown, exit by re-raised SIGTERM); 92 requests completed before it; 1 `RemoteProtocolError` at the moment of shutdown (probably a keep-alive connection being closed; not verified to be a dropped in-flight request); the remaining connection errors are the load generator still sending after the server was gone |

What this does NOT show: behaviour under sustained outage with a large escalation share, memory
growth over hours, partial network failures, a real provider's rate limits, multi-replica effects.
