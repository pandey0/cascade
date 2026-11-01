# 03 Architecture and optimisation

## Components
Gateway (FastAPI/Node) -> decision runtime -> [cache -> cheap model -> confidence -> policy] -> optional teacher call -> logger -> Postgres + object store -> trainer (batch jobs) -> registry -> dashboard. Queue (Redis/Kafka) for async logging and retraining; Postgres + pgvector for embeddings; MLflow-style registry; OpenTelemetry for tracing.

## The optimisation problem (the "real scope of work")
Given per-decision cost `c_cheap`, `c_teacher`, latency `l_cheap`, `l_teacher`, calibrated confidence `p` and an agreement target `a`:
- choose threshold `tau` minimising expected cost `c_cheap + (1 - coverage(tau)) * c_teacher` subject to selective agreement on accepted items >= `a` (with a confidence bound);
- pick the cheapest backend that meets `a` (embedding classifier < small fine-tune < fast decision model < small LLM < large LLM);
- add a **prompt/example cache** (exact + semantic) and request batching;
- **active learning:** send uncertain items to the teacher, then to the training set; cost falls over time.
Report: savings %, latency reduction, and the frontier plot (cost vs agreement).

## Calibration and guarantees
Temperature scaling and isotonic baselines; split-conformal / conformal risk control for a distribution-free bound on disagreement among accepted items, valid under exchangeability (state the assumption; drift breaks it). Re-calibrate on a rolling audit sample (e.g., 1-5% of accepted traffic sent to the teacher).

## Drift and safety
Monitor input embedding drift (PSI/MMD), label-share drift, confidence histogram shifts, audit-sample agreement. Alert and auto-fallback to teacher-only when agreement drops below target.

## Backends (pluggable)
Embeddings + logistic regression/GBM; small fine-tuned encoder; Jev-style typed decision API (optional; proprietary, verify terms); small open LLM; frontier LLM as teacher/escalation. Interface records model id, version, latency, cost per call.

## Security and ops
Per-tenant data isolation; encryption at rest/in transit; secrets in env/secret store; PII redaction option before logging; configurable retention; rate limits; idempotency keys; structured logs; Docker Compose first, Terraform/AWS later.
