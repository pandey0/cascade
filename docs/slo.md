# Service level objectives

| SLI | Definition | Objective | Window |
|---|---|---|---|
| Availability | `decisions / (decisions + teacher_unavailable + overloaded)` | 99.5% | 30 days |
| Latency | share of decisions served in <= 1 s (`cascade_decide_seconds`) | 95% | 30 days |
| Risk | lower confidence bound of audited accepted-decision error `<= alpha` | no alarm for > 5 min | continuous |

These are targets for a deployment, not measured results. The 1 s latency target assumes the
teacher path (an LLM call) is a small share of traffic; with 300 ms simulated teacher latency the
local load test is in `docs/perf.md`.

Error budget: 0.5% of requests per 30 days. Alerts (ops/prometheus/alerts.yml) page at a 14.4x
burn rate over 1 h confirmed by 5 min (budget gone in ~2 days) and open a ticket at 6x over 6 h
confirmed by 30 min, following the multi-window burn-rate method in the Google SRE Workbook
(chapter "Alerting on SLOs"). Client errors (401, 404, 413, 422, 429) are excluded from the SLI.

Excluded from "bad": the `cheap_degraded` path (served a student answer because the teacher
failed and `fail_open` is on). It is visible as its own path in `cascade_decisions_total` and
should be reviewed separately; its accuracy is the student's, not certified.
