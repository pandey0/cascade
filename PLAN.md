# Cascade (working name): a calibrated decision-cascade gateway for high-volume LLM tasks

**Status:** v0.1.0 alpha: engine, gateway, experiments and docs built (see `SCORECARD.md`, `COMPLETION-PLAN.md`); cloud deployment, CI run and demo are outstanding. Original plan text below.

> A gateway that answers structured decisions (classify, score, route, gate) with a cheap model when it is confident and escalates to an LLM only when it is not, learns from the escalations, and reports exactly how much cost and latency it saved at a stated agreement target. It combines LLM engineering, evaluation, calibration, MLOps, API design, observability and cloud deployment in one codebase.

## Research core and positioning
Closest published work is **TRACER** (arXiv 2604.14531, April 2026, open-source: surrogate trained on LLM traces behind an agreement gate). Cascade's research core extends that line: a distribution-free bounded gate versus the naive gate, drift handling with rolling recalibration, teacher-noise analysis, economics/break-even, and a production gateway. Full route, hypotheses and experiments: **`RESEARCH-ROUTE.md`**.

## What you build
1. **Decision spec** (YAML): labels or score scale, examples, teacher model, agreement target, budgets.
2. **Teacher labelling + cheap models:** embeddings + classifier first; optional small fine-tune; optional fast typed-decision backend (Jev, if access and terms allow: `../_shared/jev-notes.md`).
3. **Calibration + escalation policy:** temperature scaling/isotonic and conformal risk control; threshold chosen to minimise cost subject to the agreement target; audit sampling and auto-fallback on drift.
4. **Gateway:** `POST /decide` + OpenAI-compatible endpoint, Python and TypeScript SDKs, shadow mode (run alongside the teacher without serving), idempotency keys, rate limits, caching.
5. **Dashboard (Next.js):** cost per 1,000 decisions, latency p50/p95/p99, coverage vs agreement frontier, calibration plot, drift alerts, review queue.
6. **Platform engineering:** Postgres + pgvector, Redis, background workers, MLflow-style registry, Docker, Kubernetes (Helm/kind), Terraform + AWS, GitHub Actions, OpenTelemetry/Prometheus/Grafana.
7. **Benchmark + report:** public text-decision tasks and an agent-action-gate task; baselines (teacher-only, small-LLM-only, classical-only, strong/weak router); results with confidence intervals.

## Why it is a good portfolio piece (the point)
It shows API design, async systems, ML evaluation and calibration, cost/latency optimisation, MLOps, security, IaC and CI/CD together, on a problem every LLM team has. It reuses its evaluation harness in `../agentgate-bench/` and `../ridescore/`.

## Phases (about 12 weeks; technical gates in `docs/07`)
| Phase | Weeks | Ship |
|---|---|---|
| 1 Engine | 1-4 | spec, teacher labelling, cheap models, calibration, offline benchmark with cost accounting |
| 2 Service | 5-8 | gateway, SDKs, shadow mode, cache, workers, dashboard, CI/CD, Docker |
| 3 Platform | 9-10 | Terraform + AWS deploy, Helm/kind, observability stack, load tests, failure tests |
| 4 Polish | 11-12 | docs, runbook, threat model, demo video, results report, cost/teardown report |

Docs: `01` related work, `02` scope, `03` architecture and optimisation, `04` evaluation, `05` production readiness, `06` risks and ethics, `07` roadmap, `08` claims.
