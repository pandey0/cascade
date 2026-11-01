# Production scorecard (see ../PRODUCTION-STANDARD.md). Status is what was verified, with the command.
Legend: done = verified here; partial = some evidence; written = artefact exists but was not run/validated here; todo.

| # | Area | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Repo hygiene | partial | README with results, LICENSE, CONTRIBUTING, CHANGELOG, ADRs 0001-0005, pre-commit config. Literature check written (`docs/notes/literature-check.md`). Missing: git history/semver tag (nothing committed), diagram is ASCII |
| 2 | Code quality | done | `ruff check src tests scripts`, `ruff format --check`, `mypy` (strict) all clean (re-run at the end of this session) |
| 3 | Tests | done (unit, integration, failure-injection) | pytest `-m "not slow"` with coverage gate 85%; engine/gateway/store/artifact/drift/batching tests with fakes, teacher failure + timeout, backpressure, idempotency, backup/restore. Missing: docker-compose integration and an e2e test against a real LLM |
| 4 | CI | written | `.github/workflows/ci.yml` (lint, types, tests, exp0, gitleaks, pip-audit, docker, promtool, terraform validate, helm lint, Trivy). **Never run on GitHub** |
| 5 | CD | written | `.github/workflows/release.yml` (tag -> test, build, Trivy gate, push to GHCR, release notes from CHANGELOG); never run; no staging environment; rollback in `docs/runbook.md` |
| 6 | Containers | done | multi-stage, non-root uid 10001, healthcheck with start period, read-only FS + dropped caps tested by running it (`/healthz` 200, `/readyz` 503 with no decisions, 417 MB). **Trivy 0.58.1 (OS + Python packages, HIGH/CRITICAL, unfixed ignored): 0 findings**, 2026-11-01. Embed variant (torch) not built; base image not digest-pinned |
| 7 | IaC | partial | `infra/terraform` (ECS Fargate + ALB): `terraform fmt -check`, `init -backend=false`, `validate` pass (v1.9, 2026-11-01). `infra/helm/cascade`: `helm lint` (3.16.2) passes and `helm template` renders. **Never planned or applied** (no AWS run, no cluster/kind test) |
| 8 | Observability | partial | Prometheus metrics (tested by scraping), JSON logs with request IDs, burn-rate alert rules, Grafana dashboard JSON. `promtool check rules`: SUCCESS, 11 rules (2026-11-01). Not run against a live Prometheus/Grafana; no OpenTelemetry traces |
| 9 | Reliability | partial | timeouts, fail-open/closed, SDK retries with backoff, idempotency, rate limit, backpressure (tested), graceful shutdown via uvicorn only. No DLQ, no chaos run beyond unit-level failure injection |
| 10 | Security | partial | `docs/security.md` threat model + self-check; fail-closed auth, validation, no raw text stored, no pickle. ASVS IDs not verified against the official release; Trivy not run |
| 11 | Data | partial | versioned migrations, retention purge, online backup + restore test, hashes only. No PII review beyond notes; no data-quality checks beyond schema |
| 12 | Performance | partial | `docs/perf.md`: local A/B with simulated teacher on a contended host; dead ends reported. No k6/Locust, no clean-host numbers |
| 13 | Docs | done | architecture, runbook, SLO, security, perf, OpenAPI (`docs/openapi.json`), findings notes, results README. Missing: demo-facing walkthrough |
| 14 | Demo | partial | `scripts/demo.sh` + `docs/demo.md` + captured transcript (real student/encoder, simulated teacher); no video; cost report `results/economics.md`; teardown N/A (nothing deployed) |

**Count:** 4 done (2, 3, 6, 13), 10 partial/written, 0 todo; validators run for rules, Terraform, Helm and the image. This is below the 12/14 target if only "done" counts: the gaps are mostly things that need accounts, time or your decision (CI run, cloud apply, demo, clean-host load test).
