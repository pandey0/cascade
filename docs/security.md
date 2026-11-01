# Security: threat model and ASVS-style self-check

Scope: the gateway (`src/cascade/gateway`, `engine.py`, `store.py`). Status: self-assessment, not
an audit. ASVS IDs are cited in the section below.

## Assets and trust boundaries
Inputs (customer text, possibly personal data) -> gateway -> third-party LLM API (the teacher) and
a local SQLite audit store. API keys for clients and for the teacher provider. Student weights.

## Threats and controls
| # | Threat | Control (where) | Residual risk |
|---|---|---|---|
| 1 | Unauthenticated use / cost abuse; key guessing | API-key header, constant-time compare, fail-closed when no keys; scopes; per-key token bucket; failed-auth lockout per address (`gateway/app.py`) | Keys are static shared secrets; in-memory limiters are per replica |
| 2 | Oversized or malformed input | pydantic validation, 413 over `CASCADE_MAX_INPUT_CHARS` (4000), 422 on bad shape | Prompt injection into the teacher cannot change a closed label set (output constrained to an enum) but can steer which label is chosen |
| 3 | Teacher output outside the label set | schema-constrained output + validation; invalid -> `__invalid__` | An `__invalid__` audit counts as disagreement |
| 4 | Secrets leakage | keys only from env, never logged, cached or in manifests; `.env` gitignored; gitleaks in CI | `.env` on disk is plain text; use a secret manager in deployment |
| 5 | PII retention | store keeps only SHA-256 of input text, never raw text; retention purge (`AuditStore.purge_older_than`) | Hashes of short texts are guessable; the teacher provider sees raw text (check its retention terms) |
| 6 | Resource exhaustion | concurrency limit -> 503 + Retry-After, timeouts on teacher calls, bounded batch queue per worker | No global (cross-replica) limit |
| 7 | Replay / double-spend | `Idempotency-Key` returns the stored response without calling the teacher again | Key space is per decision, 128 chars |
| 8 | Supply chain | `pip-audit` and gitleaks in CI; pinned base image tag; non-root container, read-only FS, all capabilities dropped (`docker-compose.yml`) | Base image not digest-pinned; Trivy scan not yet run |
| 9 | Model/weights tampering | student stored as plain arrays loaded with `allow_pickle=False` | No signature on the artifact |
| 10 | Metrics exposure | `/metrics` has no auth by design (scrape from inside the network) | Must not be exposed publicly; put behind the cluster network policy |

## ASVS 5.0.0 Level 1 self-check (2026-11-01)
Source: OWASP ASVS 5.0.0 CSV (`OWASP/ASVS`, `5.0/docs_en`), read through a fetch tool that
summarises long pages: requirement IDs and one-line meanings below come from that read; the output
was cut off partway through chapter V16, so V16 is not covered and the L1 list for other chapters
may be incomplete. This is a developer self-assessment, not an audit. Items for browser sessions,
passwords, OAuth, files and WebSockets do not apply (stateless JSON API with API keys).

| ASVS | Requirement (short) | Status | Where / how |
|---|---|---|---|
| V1.2.4 | parameterised queries | met | all SQL uses `?` parameters (`store.py`); the only f-string is an integer in a PRAGMA |
| V1.2.5, V1.3.2 | no OS command injection / eval | met | no shell calls or eval in the service |
| V2.1.1 | document input validation rules | met | pydantic models, OpenAPI (`docs/openapi.json`), size limit in this document |
| V2.2.1 / V2.2.2 | allow-list validation, enforced server-side | met | pydantic types + length bounds, 413 over `CASCADE_MAX_INPUT_CHARS`, `Idempotency-Key` 1-128 chars |
| V3.4.1 | HSTS on all responses, >= 1 year | met in app, effective only behind TLS | `Strict-Transport-Security: max-age=31536000; includeSubDomains` (tested); TLS itself is terminated at the load balancer (Terraform has an HTTPS listener with redirect when `certificate_arn` is set; default is plain HTTP for demos) |
| V3.4.2 | fixed CORS allow-origin | met | no CORS middleware, no `Access-Control-Allow-Origin` header (tested) |
| V4.1.1 | Content-Type matches content | met | JSON responses; `/metrics` as `text/plain` |
| V6.1.1 | document rate limiting / anti-automation | met | per-key token bucket (429) and failed-auth lockout per client address (429, `CASCADE_AUTH_FAIL_PER_MIN`, default 20) |
| V6.3.1 | brute-force controls | met | failed-auth lockout (tested); keys compared in constant time; locked-out addresses are refused even with a valid key |
| V6.3.2 | no default accounts | met | no default keys; fails closed without configured keys |
| V8.1.1 / V8.2.1 | documented, function-level access rules | met | scopes: `decide` or `decide:<name>`, `status`, `admin` (recalibration needs `admin`); plain keys get `decide`+`status`; 403 otherwise (tested) |
| V8.2.2 | data-level access (IDOR/BOLA) | partial | `decide:<name>` restricts a key to one decision; there are no per-tenant records to enumerate; audit data is not exposed through the API |
| V8.3.1 | authorisation at a trusted layer | met | enforced server-side in every `/v1` route |
| V13.4.1 | no source-control metadata deployed | met | image copies only the built wheel; `.dockerignore` |
| V14.2.1 | no sensitive data in URL/query | met | keys in headers, inputs in the body; no inputs are logged |
| V12 (TLS) | secure communication | partial | depends on deployment; Terraform HTTPS option written and validated, never applied |
| V16 | logging and error handling | not assessed | text cut off; implemented: structured logs without input text, request IDs, `auth_failed` warnings (no key material), no stack traces in responses |
| V11/V13.3 | cryptography / secrets | partial | secrets only from env or a secret manager; no key rotation tooling |

## Open items
Run the full ASVS CSV through a script rather than a summarising fetch and re-check V16 and
the chapters it cut off; Trivy on every release (CI does this); digest-pin base images; a
secret-manager integration for the teacher key; key rotation procedure; verify behaviour behind
a real TLS terminator.
