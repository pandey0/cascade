# Changelog
All notable changes to this project. Format: Keep a Changelog; versioning: SemVer.

## [0.1.0] - 2026-11-01 (unreleased: not tagged or pushed)
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
### Security
- Failed-auth lockout per client address, per-key scopes (`decide[:name]`, `status`, `admin`; recalibration needs admin), security headers (HSTS, nosniff, no-store on /v1), auth-failure logging, optional HTTPS listener in Terraform. ASVS 5.0.0 L1 self-check in `docs/security.md`.
### Changed
- Plain API keys no longer allow `POST /v1/recalibrate/*` (needs an `admin`-scoped key: `CASCADE_API_KEYS=key@admin`).
- Gateway skeleton replaced; `create_app` now takes engines, settings and a store.
