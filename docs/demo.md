# Demo walkthrough (local, reproducible)

`scripts/demo.sh` starts the gateway with a real Banking77 student, the real MiniLM encoder, API-key
auth, a 50% audit rate and a **simulated teacher** (300 ms, returns the dataset's gold label), then
sends real held-out messages. No paid API is called. Captured output: `evidence/logs/demo_transcript.txt`.
(The first 60 held-out messages are in dataset order, so most are about card arrival.)

What the transcript shows:
1. A request without an API key is rejected (`401`, fail-closed).
2. Six held-out messages were answered on the **cheap path** (the student was above the certified
   threshold 0.475) with their confidences.
3. Idempotency: the same `Idempotency-Key` twice returns the second response with `idempotent-replay: true`.
4. An oversize input gets `413`.
5. After 60 requests: `GET /v1/status/banking77` shows 28 audits, 30 teacher calls (audits plus
   escalations), no drift alarm; `/metrics` shows 54 cheap and 6 teacher decisions, the threshold
   and the risk monitor's bound (clamped at 0) as Prometheus gauges.

A lesson from building this demo: with hand-typed messages the simulated teacher returned a default
label, the student "disagreed", and the drift alarm fired (risk bound 0.56). The alarm was right
about the data it saw and wrong about the world; always check what the audit reference is before
trusting an alarm (`docs/runbook.md`, drift section).

Video: `docs/img/demo_replay.mp4` (41 s) is a typed **replay** of this captured transcript with captions, made by `scripts/make_demo_video.py`; the live Grafana capture is `docs/img/grafana_dashboard.jpg`. Not included: a narrated 2-3 minute screen recording (needs you) and a run against a real LLM teacher.
