# 01 Related work (engineering references, not a market gate)
Know the neighbours so your design is informed and your write-up honest. Verify each from its own docs (research 2026-11-01 was from secondary sources).
- **LLM gateways/routers:** LiteLLM (open-source proxy), Portkey (observability/guardrails), OpenRouter (hosted aggregator). Study their API surface, logging and budget features.
- **Routing research:** RouteLLM (strong/weak routing; self-reported savings on its benchmarks) and FrugalGPT (cascades, approximation, prompt adaptation; reports large cost reductions on its tasks). Read both papers; reproduce one baseline.
- **Distillation from logs:** products and papers that train small models from LLM logs: read how they handle calibration and drift.
- **Conformal prediction / selective classification:** foundations for the agreement guarantee.
- **Fast typed-decision models** (Jev): see `../_shared/jev-notes.md`.
Deliverable: a 1-page "design inspirations and differences" note in the repo.

## Update 2026-11-01 (verified at abstract level this session)
- **TRACER** (arXiv 2604.14531): trace-trained surrogate + parity gate (alpha), open-source; closest prior work: read it first.
- **Gupta et al., ICLR 2024 (arXiv 2404.10136):** learned deferral rules; token-level uncertainty; embeddings help.
- **Conformal abstention (arXiv 2405.01563):** distribution-free bound on hallucination rate via a calibrated threshold.
- Also seen: UniCR (arXiv 2509.01455), RouteLMT (arXiv 2604.22520), learned abstention thresholds (arXiv 2502.06884), CanDist (arXiv 2506.03857).
See `../RESEARCH-ROUTE.md` for how each is used.
