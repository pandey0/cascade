# Security: threat model and ASVS-style self-check

Scope: the gateway (`src/cascade/gateway`, `engine.py`, `store.py`). Status: self-assessment, not
an audit. ASVS requirement IDs are deliberately not cited: they must be taken from the official
OWASP ASVS release, which has not been checked against this repo yet (open item).

## Assets and trust boundaries
Inputs (customer text, possibly personal data) -> gateway -> third-party LLM API (the teacher) and
a local SQLite audit store. API keys for clients and for the teacher provider. Student weights.

## Threats and controls
| # | Threat | Control (where) | Residual risk |
|---|---|---|---|
| 1 | Unauthenticated use / cost abuse | API-key header, constant-time compare, fail-closed when no keys (`gateway/app.py`); per-key token bucket | Keys are static shared secrets; in-memory limiter is per replica |
| 2 | Oversized or malformed input | pydantic validation, 413 over `CASCADE_MAX_INPUT_CHARS` (4000), 422 on bad shape | Prompt injection into the teacher cannot change a closed label set (output constrained to an enum) but can steer which label is chosen |
| 3 | Teacher output outside the label set | schema-constrained output + validation; invalid -> `__invalid__` | An `__invalid__` audit counts as disagreement |
| 4 | Secrets leakage | keys only from env, never logged, cached or in manifests; `.env` gitignored; gitleaks in CI | `.env` on disk is plain text; use a secret manager in deployment |
| 5 | PII retention | store keeps only SHA-256 of input text, never raw text; retention purge (`AuditStore.purge_older_than`) | Hashes of short texts are guessable; the teacher provider sees raw text (check its retention terms) |
| 6 | Resource exhaustion | concurrency limit -> 503 + Retry-After, timeouts on teacher calls, bounded batch queue per worker | No global (cross-replica) limit |
| 7 | Replay / double-spend | `Idempotency-Key` returns the stored response without calling the teacher again | Key space is per decision, 128 chars |
| 8 | Supply chain | `pip-audit` and gitleaks in CI; pinned base image tag; non-root container, read-only FS, all capabilities dropped (`docker-compose.yml`) | Base image not digest-pinned; Trivy scan not yet run |
| 9 | Model/weights tampering | student stored as plain arrays loaded with `allow_pickle=False` | No signature on the artifact |
| 10 | Metrics exposure | `/metrics` has no auth by design (scrape from inside the network) | Must not be exposed publicly; put behind the cluster network policy |

## Self-check against typical ASVS-L1-style areas
Authentication (static API keys: partial), session management (n/a, stateless), access control
(single role: partial), input validation (done), output encoding (JSON only), error handling (no
stack traces returned: done), logging (structured, no input text: done), data protection
(minimal retention: partial), communications (TLS terminated outside the app: to be configured
in deployment), configuration (env-based, secure defaults: done), dependencies (audit in CI).

## Open items
Verify against the official ASVS release; Trivy on the image; digest-pin base images; per-key
scopes; a secret-manager integration for the teacher key.
