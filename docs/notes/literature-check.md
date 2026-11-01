# Literature check (2026-11-01; search results and arXiv abstract pages, NOT full reads)

Goal: decide what this project may and may not claim. Method: web searches plus arXiv abstract
pages for titles/authors/dates. Papers marked "abstract only" were not read in full.

| Work | Relevance | Overlap with Cascade |
|---|---|---|
| Geifman & El-Yaniv 2017, *Selective Classification for Deep Neural Networks* (arXiv 1705.08500) | Selects a confidence threshold for a trained classifier so error <= r* with probability >= 1-delta; per a NeurIPS review it uses a binomial bound, binary search and a Bonferroni correction | **High.** Our Bonferroni gate is essentially this algorithm on a fixed grid. Not novel. Cite as the origin of certified selection |
| Angelopoulos, Bates et al., *Learn then Test* (2110.01052) | Risk control as multiple testing with finite-sample guarantees | **High.** Bonferroni/Holm/fixed-sequence are LTT-style procedures. Not novel |
| TRACER (Rida, 2604.14531) | Trace-trained surrogates behind an agreement gate for LLM classification; code with one-shot certification | **High** for the cascade idea; we never claim it |
| Conformal Cascade (Dou, Lian, Li; 2607.25018; abstract only) | Multi-tier LLM cascade with distribution-free finite-sample accuracy guarantee via conformal set size, per-tier calibration | Medium: same family (certified deferral), different guarantee (accuracy vs gold-labelled calibration; multiple-choice benchmarks) |
| BalanceRAG (Jia et al.; 2605.20084; abstract only) | Joint risk calibration of cascaded RAG with sequential graphical testing over a 2-D threshold grid | Medium: multi-threshold certified routing |
| Certified deferral for small LMs (2608.05064; search snippet only) | Clopper-Pearson certificate on a 200-question calibration set | Medium: same exact-bound idea |
| Podkopaev & Ramdas (2110.06177); Waudby-Smith & Ramdas (2010.09686) | Anytime-valid risk monitoring; the confidence sequence we implement | We implement an existing method; no novelty claimed |
| Gupta et al. 2024 (2404.10136); Yadkori et al. 2024 (2405.01563); FrugalGPT | Cascades / conformal abstention for LLMs | Background |

## What this means for claims
- **Not claimable as new:** the cascade idea, certified threshold selection (Geifman & El-Yaniv, LTT), anytime-valid monitoring.
- **What the project can honestly offer:** an empirical comparison of selection procedures in the LLM-distillation setting, including the failure of naive selection and of strict-start fixed-sequence designs; evidence that *agreement with an imperfect LLM teacher* is neither sufficient nor necessary for gold correctness; a small drift/audit-budget study; an engineered, tested gateway. These are applied/empirical contributions of modest size.
- **Still unchecked:** whether any paper already reports the teacher-noise or audit-window findings; the full texts of the medium-overlap papers (they may report comparable experiments); published venues of several entries. Do a full read of Geifman & El-Yaniv and Conformal Cascade before writing any "related work" claim that compares guarantees.
