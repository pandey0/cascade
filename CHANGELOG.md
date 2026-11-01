# Changelog
All notable changes to this project. Format: Keep a Changelog; versioning: SemVer.

## [0.1.0] - 2026-11-01
### Added
- Failure-injection script and results (`scripts/chaos.py`, `docs/reliability.md`), audit data-quality checks (`quality.py`), live Prometheus verification of the alert rules.
- Decision engine with uniform audit sampling, rolling Holm recalibration, shadow mode, fail-open/closed teacher policy, anytime-valid (PrPl-EB) drift alarm.
- Gateway: API-key auth (fail-closed), validation, rate limiting, idempotency keys, concurrency backpressure, request IDs, Prometheus metrics, JSON logs, status and recalibrate endpoints.
- SQLite audit store with versioned migrations, retention, online backup/restore; no raw text stored.
- Teacher adapters for Claude and Gemini (schema-constrained labels, cost accounting); labelling script with dry-run and spend cap.
- Student persistence without pickle, deployable artifact format, `create_app_from_env`.
- Micro-batching of embeddings; break-even economics model.
- Experiments: exp1b (noisy LLM teacher), exp2 (drift streams); findings notes; ADR 0005.
- Ops: Prometheus recording/alert rules (multi-window burn rate), Grafana dashboard, SLO, security, runbook docs; Terraform and Helm (unapplied).
### Documentation
- Prompt-caching probe (`scripts/caching_probe.py`, 24 real calls): 7.2x cheaper per call; economics and comparison updated with the measured factor.
- Experiment 3 (head-to-head comparison with alternatives): `scripts/compare_approaches.py`, `scripts/summarize_compare.py`, `docs/notes/comparison-{plan,findings}.md`, figures 7 and 8; critique and README updated with the result.
- `docs/critique.md`: adversarial review with outside research, hosting-aware economics, two measured defects and a prioritised fix list; corrected a doc claim about a retraining flywheel; `economics.py` gained daily break-even and payback functions.
- README rewritten problem-first (problem, where Cascade fits, a verified 2-minute quickstart, results, when not to use it); long narrative moved to `docs/story.md`, evidence to `docs/evidence.md`; `examples/quickstart.py` added and linted in CI.
### Verified
- CI on GitHub (py3.10/3.12 tests, security, docker, ops, Trivy); Helm chart installed on a k3s cluster (rolling restart under load, 553/553 OK); live Prometheus + Grafana (all panels return data); `promtool`, `terraform validate`, Trivy; Locust A/B with CPU and memory (`docs/perf.md`); failure-injection scenarios (`docs/reliability.md`).
### Fixed
- Audits (teacher label, database write, re-tuning) now run on background workers behind a bounded queue: confident audited requests no longer wait for the teacher (p95 306 ms -> 0.007 ms in `scripts/measure_defects.py`), and a failed audit write no longer returns HTTP 500.
- Teacher calls: pool sized to the concurrency limit, slots held until the call really ends, fail-fast when saturated, timeouts enforced in the Claude and Gemini HTTP clients (recovery after a stalled teacher 2.5 s -> 0.0006 s). New settings: `teacher_workers`, `audit_workers`, `audit_queue_size`, `teacher_timeout_s`; new metrics `cascade_audit_queue_depth`, `cascade_audits_dropped`, `cascade_teacher_in_flight`; new alert `CascadeAuditsDropping`.
### Security
- Failed-auth lockout per client address, per-key scopes (`decide[:name]`, `status`, `admin`; recalibration needs admin), security headers (HSTS, nosniff, no-store on /v1), auth-failure logging, optional HTTPS listener in Terraform. ASVS 5.0.0 L1 self-check in `docs/security.md`.
### Changed
- Plain API keys no longer allow `POST /v1/recalibrate/*` (needs an `admin`-scoped key: `CASCADE_API_KEYS=key@admin`).
- Gateway skeleton replaced; `create_app` now takes engines, settings and a store.
