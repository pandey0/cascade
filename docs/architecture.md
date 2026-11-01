# Architecture

```
client ──HTTP──► gateway (FastAPI)          Engine                          Teacher (LLM API)
                 auth · validate ·    ┌─────────────────────────┐        ┌───────────────────┐
                 rate limit ·         │ embed ► student ► conf  │        │ Claude / Gemini   │
                 idempotency ·        │ conf >= threshold?      │─ no ──►│ schema-constrained│
                 backpressure         │   yes: cheap answer     │        │ label + cost      │
                 /metrics /healthz    │ audit (random r):       │─ r ───►│ (timeout, retry)  │
                 /readyz              │   also ask the teacher  │        └───────────────────┘
                      │               │ recalibrate (Holm) on   │
                      │               │   the audit window      │──► AuditStore (SQLite: hashes,
                      ▼               │ drift alarm (PrPl-EB CS)│     confidence, labels; migrations,
                 Prometheus ► Grafana └─────────────────────────┘     backup, retention)
```

| Module | Responsibility |
|---|---|
| `bounds.py`, `gates.py` | exact binomial bounds; threshold selection methods (the research core) |
| `engine.py` | per-request decision, audit sampling, recalibration, fail-open/closed policy |
| `drift.py` | anytime-valid risk monitor, drift stream simulator |
| `store.py` | audit store, idempotency table, migrations, backup |
| `gateway/app.py` | HTTP surface, security and reliability controls, metrics, structured logs |
| `artifact.py` | deployable bundle (student arrays + JSON settings) and the uvicorn factory |
| `adapters/` | Claude and Gemini teachers (closed-set JSON, cost accounting) |
| `batching.py` | micro-batching of embedding calls |
| `economics.py` | break-even model |
| `sim.py`, `bench.py`, `cli.py`, `provenance.py` | experiments, CLI, run manifests and ledger |

Key invariants: (1) only uniformly random audits (or every item in shadow mode) feed calibration;
(2) the gate withdraws (escalate all) when nothing certifies; (3) no raw input text is stored;
(4) the teacher key never leaves the environment; (5) experiments write a manifest with the
source-tree hash, so every number traces to code.
Decisions: `docs/adr/`. Operations: `docs/runbook.md`, `docs/slo.md`. Threats: `docs/security.md`.
