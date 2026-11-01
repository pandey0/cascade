# ADR 0002: Position Cascade as an extension of TRACER-style trace distillation
Status: accepted (2026-11-01).
**Context.** TRACER (arXiv 2604.14531; MIT) already implements the core idea: a surrogate trained on LLM traces behind an agreement gate, with one-shot certification in the current repo. See `docs/notes/tracer-analysis.md`.
**Decision.** Credit TRACER precisely; do not claim the core idea. Contribute: certified threshold selection (E1), audit sampling with weighting (E2), anytime-valid monitoring (E3), teacher-noise-aware risk (E4), a cost model (E7), optional tiers with open typed-decision models (E6), and a production gateway (E9). Pin the compared TRACER commit. Consider upstreaming E1/E2.
**Consequences.** A smaller, honest research claim; a write-up that is a careful extension and evaluation; no code copied from TRACER without attribution (it is MIT, so attribution suffices).
