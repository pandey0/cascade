# 05 Production readiness (Cascade-specific, on top of `../../PRODUCTION-STANDARD.md`)
- **Reliability:** per-request timeouts; teacher-call retries with backoff + jitter; circuit breaker to cheap-only or teacher-only mode; idempotency keys; request deduplication; DLQ for failed async logging; graceful shutdown; queue backpressure.
- **Performance targets (measure, then publish):** cheap path p95 < 30 ms at your chosen load; gateway overhead on the teacher path < 15 ms; throughput target (e.g., 500 req/s on a small instance); load tests with k6; profile and fix one hotspot with before/after numbers.
- **Multi-tenancy (even if only demonstrated):** tenant-scoped keys, row-level isolation tests, per-tenant budgets and rate limits.
- **Observability:** per-decision trace (cheap score, threshold, escalated?, teacher latency/cost); Prometheus metrics (coverage, agreement on audit, cost/1k, queue depth); Grafana dashboards; alerts for agreement drop, drift, budget burn.
- **MLOps:** versioned decision specs and models; model registry; shadow mode; canary by traffic percentage; rollback; retrain job (scheduled) with a CI quality gate (agreement and calibration must not regress).
- **Security:** threat model (API keys, tenant data, prompt/response logs, teacher credentials); secrets in env/secret store; PII redaction option; log retention; dependency scanning; SBOM optional.
- **Infra:** Docker Compose dev; Helm chart/kind for gateway and workers; Terraform for AWS (VPC, ECS/EKS or EC2, RDS Postgres, ElastiCache or Redis container, ECR, CloudWatch/Grafana); cost estimate and one-command teardown.
- **Scorecard:** track the 14-point scorecard in this folder (`SCORECARD.md`) with links as you go.
