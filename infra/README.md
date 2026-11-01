# Infrastructure

`terraform/`: AWS ECS Fargate behind an ALB, ECR, Secrets Manager (values set out of band),
CloudWatch logs. `helm/cascade/`: Kubernetes chart (Deployment, Service, probes, securityContext,
PodDisruptionBudget, NetworkPolicy).

**Helm chart: tested on a real cluster (2026-11-01).** A single-node k3s v1.31.2 (privileged container,
local, since removed) ran `helm install` of this chart with the packaged gateway image and a demo
artifact (hashing embedder, Banking77, mounted from a ConfigMap): both replicas became Ready;
through the Service `/readyz` returned 200, requests without a key 401, a read-only key got 403 on
recalibration and an admin key 200; the pod ran as uid 10001 with a read-only root filesystem and no
capabilities; the PodDisruptionBudget existed; a **rolling restart under continuous traffic served
553 of 553 requests with HTTP 200** (p50 32 ms, p99 121 ms, max 410 ms). Logs:
`evidence/logs/k8s_smoke_1.txt`, `k8s_smoke_2.txt`. Limits: single node, dummy teacher key (no LLM
call), no ingress/TLS, no HPA, no NetworkPolicy enforcement test (k3s default CNI), image loaded
directly rather than pulled from a registry.

**Terraform:** `terraform fmt`, `init` and `validate` pass locally and in CI; it has **never been planned
or applied** (that creates billable AWS resources).

Before applying anything: `terraform fmt && terraform validate` (needs terraform >= 1.6),
`helm lint infra/helm/cascade`, then a `plan` you have read. Set `allowed_cidrs` to your IP.

Cost (verify on the AWS pricing pages before use; these are shapes, not quotes): the ALB has an
hourly charge plus per-LCU usage even when idle, Fargate bills per vCPU-second and GB-second for the
running task, CloudWatch bills ingestion and storage, Secrets Manager bills per secret per month.
The idle ALB is usually the largest fixed line, so destroy when not demonstrating.

Teardown: `terraform destroy` (ECR uses `force_delete`, so images go too). Delete the two
secrets' scheduled-deletion window manually if you want the names back immediately.
