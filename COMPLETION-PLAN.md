# Cascade completion plan (written 2026-11-01, before implementation)

**Goal:** finish Cascade to the standard in `../PRODUCTION-STANDARD.md` (12+/14 with evidence) and bring the research to a
defensible preprint-ready state. Anything needing accounts, money or publication is listed under "User-side"; I do not do
those without an explicit yes. No commits or pushes unless asked.

## What "done" means
| Track | Done when |
|---|---|
| R research | Experiments for RQ3 (drift + audit sampling), RQ4 follow-up (gold-risk audit), RQ5 (economics) have run from one `make` target, with manifests; paper + CLAIMS.md match the evidence; literature check written; a TRACER-package baseline is run on identical splits or its absence is documented |
| E engineering | SCORECARD >= 12/14 with each "done" backed by a command that passes (tests, lint, types, container, load test, validated IaC); honest limits documented |

## Research needed before building (findings from search snippets; read the sources before citing)
- Podkopaev & Ramdas, *Tracking the risk of a deployed model and detecting harmful distribution shifts* (arXiv 2110.06177): anytime-valid
  (betting) confidence sequences for monitoring risk; fixed-time bounds inflate false alarms under continuous monitoring. -> basis for the drift monitor.
- Angelopoulos, Bates et al., *Learn then Test* (arXiv 2110.01052): risk control as multiple testing; our Bonferroni/Holm gates are instances.
- Hultberg et al. (growing-calibration risk control) and weighted CRC under covariate/label shift (Zecchin; Podkopaev & Ramdas label shift): related work for rolling recalibration.
- Search snippets claim monotone recalibration (temperature/isotonic) leaves a threshold-based accept set unchanged: verify, then explain why our temperature scaling does not change gates.
- Not found in one paper: finite-sample selective-classification guarantee under shift with online recalibration. A positioning claim of novelty is NOT allowed until a proper literature check is done (task R5).
- Standards to follow: Google SRE Workbook multi-window burn-rate alerts; OWASP ASVS (use the official release for IDs, not third-party lists); Prometheus naming; OpenTelemetry semantic conventions; 12-factor config.

## Design decisions (ADR 0005, 0006 to write)
1. **Audit sampling (R1).** A fraction r of served decisions is randomly sent to the teacher regardless of confidence, giving unbiased labelled data
   on the *accepted* population. Uniform random is the only unbiased option without weights; importance-weighted sampling is a stretch goal.
2. **Rolling recalibration.** Keep a sliding window of audit labels; re-run Holm on the window every K decisions; if no threshold is certifiable, fall back to escalate-all. Cost: coverage drops after shift, risk target preserved if the window is exchangeable with current traffic.
3. **Drift monitor.** Betting-based confidence sequence on the audited error of accepted items; alarm when the lower bound exceeds alpha. Compare with a naive fixed-window test to show false-alarm inflation.
4. **Gold-risk audit (follow-up to exp1b).** If a small gold-labelled audit is available, certify gold risk directly (Clopper-Pearson on audit errors vs gold). Show cost in labels.
5. **Economics (R3).** Closed-form break-even: volume V where savings = labelling + training + audit cost; sensitivity to coverage, teacher price, audit rate. Property-tested.

## Work order (each step ends with tests + lint + mypy + evidence)
| # | Step | Output |
|---|---|---|
| 1 | Research notes + ADR 0005/0006 | `docs/notes/drift-related-work.md`, ADRs |
| 2 | `cascade/drift.py`: confidence sequence, windowed recalibration, stream simulator; tests incl. false-alarm calibration | exp2 on synthetic + real pools |
| 3 | `cascade/economics.py` + notebook + tests | break-even figure |
| 4 | Gold-risk audit gate + exp1c | table + CLAIMS rows |
| 5 | Gateway hardening: artifact load, shadow mode, audit endpoint, idempotency, timeouts/retries, rate limit, graceful shutdown, API-key auth, input limits | integration + failure-injection tests |
| 6 | Observability: structured logs, Prometheus metrics, /readyz, burn-rate alert rules, Grafana JSON | files + tests that scrape /metrics |
| 7 | Data: SQLite audit store with versioned migrations, backup/restore test, retention note | tests |
| 8 | Perf: Locust (or asyncio) load test, p50/p95/p99, one profile-and-fix with before/after | `docs/perf.md` |
| 9 | Security: threat model, ASVS L1 self-check from the official release, pip-audit, gitleaks config | `docs/security.md` |
| 10 | IaC: Terraform + Helm written, `terraform validate` / `helm lint` run if tools exist; NOT applied | `infra/`, cost + teardown notes |
| 11 | Docs + repo hygiene: README with real results, CHANGELOG, CONTRIBUTING, pre-commit, runbook, OpenAPI export, SCORECARD with links, TRACER baseline attempt, paper update, literature check | final report |

## Stop conditions
- If a research result contradicts a hypothesis, report it; do not tune on the evaluation pools.
- If a tool is missing (terraform, helm, k6, trivy), write the artefact, record "unvalidated: tool absent" in the SCORECARD rather than claiming done.
- Spend: no new API spend without telling you first (all planned work is offline; the Claude teacher labels are cached).

## User-side (I will not do these)
Run CI on GitHub (push), AWS deploy/teardown, demo video, publish/arXiv, employer-agreement check, rotating exposed keys.
