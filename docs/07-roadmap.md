# 07 Roadmap and technical gates (12 weeks, 8-10 h/week)
**Weeks 1-6 are detailed day by day in `../RESEARCH-ROUTE.md` section 5; that route takes precedence.**

| Week | Work | Gate (evidence) |
|---|---|---|
| 1 | repo scaffold, CI (lint/type/test/gitleaks), ADR template, related-work note, teacher labelling harness with cost accounting | CI green; 1 public text task labelled by teacher |
| 2 | cheap models (embeddings+classifier), splits, metrics code | baseline table |
| 3 | calibration (temperature/isotonic) + selective-risk curves | reliability plots |
| 4 | cascade policy with agreement target + conformal bound; audit sampling | cost/agreement frontier on 3 tasks with CIs. GATE: if no savings at target agreement, publish the negative result and the harness, then continue with the service as an engineering exercise |
| 5 | gateway `/decide`, Postgres schema + migrations, Redis cache, idempotency, rate limits | integration tests green |
| 6 | OpenAI-compatible endpoint, SDKs (Python/TS), shadow mode | SDK e2e tests |
| 7 | workers (async logging, retrain), registry, canary, rollback | rollback drill documented |
| 8 | dashboard (Next.js), review queue | demo video v1 |
| 9 | observability (OTel, Prometheus, Grafana), SLOs, alerts | dashboards + alert test |
| 10 | Terraform + AWS deploy, Helm/kind, load tests, failure tests | load/failure reports; cost report; teardown script |
| 11 | agent action-gate task using the harness; optional Jev backend; threat model | benchmark task added |
| 12 | docs, runbook, scorecard, final report, demo video | scorecard >= 12/14 |
Weekly rhythm: weekday 30-60 min, one weekend block, `JOURNAL.md`.
