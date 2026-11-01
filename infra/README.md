# Infrastructure (written, NOT applied or validated)

`terraform/`: AWS ECS Fargate behind an ALB, ECR, Secrets Manager (values set out of band),
CloudWatch logs. `helm/cascade/`: Kubernetes chart (Deployment, Service, probes, securityContext,
PodDisruptionBudget, NetworkPolicy). Neither has been run: `terraform`, `helm` and `kind` are not
installed on the dev machine, and applying Terraform creates billable resources.

Before applying anything: `terraform fmt && terraform validate` (needs terraform >= 1.6),
`helm lint infra/helm/cascade`, then a `plan` you have read. Set `allowed_cidrs` to your IP.

Cost (verify on the AWS pricing pages before use; these are shapes, not quotes): the ALB has an
hourly charge plus per-LCU usage even when idle, Fargate bills per vCPU-second and GB-second for the
running task, CloudWatch bills ingestion and storage, Secrets Manager bills per secret per month.
The idle ALB is usually the largest fixed line, so destroy when not demonstrating.

Teardown: `terraform destroy` (ECR uses `force_delete`, so images go too). Delete the two
secrets' scheduled-deletion window manually if you want the names back immediately.
