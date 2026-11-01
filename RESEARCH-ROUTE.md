# Cascade research and build route

Written 2026-11-01. Goal: a defensible, reproducible research core under the production system described in `PLAN.md`. IndicRAG is out of scope here. Sources I actually read this session are marked **[read]** (abstract level only); items marked **[recalled]** are from general knowledge and must be verified before you cite them.

## 1. Where Cascade sits (honest positioning)
- **Closest prior work: TRACER** (Rida, arXiv 2604.14531, submitted 2026-04-16, open-source: github.com/adrida/tracer) **[read, abstract only]**. A lightweight surrogate is trained on an LLM's production traces; a "parity gate" activates it only when its agreement with the LLM exceeds a user threshold alpha; reports 83-100% surrogate coverage on a 77-class intent benchmark depending on alpha, full replacement on a 150-class benchmark, and *refusal to deploy* on an NLI task where embeddings separate poorly; teacher reported as Sonnet 4.6; the abstract does not describe a formal guarantee beyond the gate, nor cost numbers.
- **Cascade/deferral theory:** Gupta et al., "Language Model Cascades: Token-level uncertainty and beyond", ICLR 2024 (arXiv 2404.10136) **[read]**: learned post-hoc deferral rules beat simple sequence-level uncertainty; embeddings help. FrugalGPT (Chen, Zaharia, Zou 2023; arXiv 2305.05176) **[read via search]**. RouteLLM, AutoMix, Hybrid LLM **[recalled]**; RouteLMT (arXiv 2604.22520) **[seen in search]**.
- **Guarantees:** conformal abstention for LLM hallucination (Abbasi Yadkori et al., arXiv 2405.01563) **[read]**; selective/conformal risk control and UniCR (arXiv 2509.01455) **[seen]**; learned abstention thresholds (arXiv 2502.06884) **[seen]**; Conformal Risk Control (Angelopoulos et al.), Learn-then-Test (Angelopoulos et al.), Distribution-free risk-controlling prediction sets (Bates et al.), selective classification (Geifman and El-Yaniv), temperature scaling (Guo et al. 2017), reject option (Chow) **[recalled]**.
- **LLM-as-annotator distillation:** CanDist (arXiv 2506.03857), others **[seen in search]**.

**Consequence:** the idea is not novel and does not need to be (your goal is a production-grade engineering project). The research core should be a *careful, honest extension and evaluation*: reproduce the TRACER-style gate, then test whether a distribution-free guarantee, drift handling and cost accounting make the gate safer and more useful. If a result is already in TRACER's full paper, say so and cite it.

## 1b. Update after reading TRACER's paper and repo (2026-11-01)
Full analysis: `docs/notes/tracer-analysis.md`. Three consequences for this route:
1. The repo already **certifies the final policy once** (one-sided Clopper-Pearson lower bound on a reserved 20% split, `certification_alpha=0.10`, no retries; does not cover shift or adaptive reuse). So RQ1 is no longer "bounded vs naive": it is **certified selection (fixed-sequence over a fixed grid) vs naive selection vs certify-once**, i.e., how much coverage does each recover at a given validity level. Experiment 0 (synthetic, done: `results/`, `docs/notes/exp0-findings.md`) already shows naive misses its target about half the time and that certification's cost is audit data.
2. TRACER's docs advise including representative traffic, not only old-policy deferrals, but provide no sampler or statistics: **RQ3 gains an audit-sampling arm** (E2) and a **sequential-monitoring arm** (E3).
3. Teacher accuracy is 81% on Banking77 in the paper: **RQ4 (teacher noise) becomes central** (E4).
Extension IDs E1-E10 refer to the table in `docs/notes/tracer-analysis.md`.

## 1c. Results so far (2026-11-01; details in `docs/notes/exp1a-findings.md`)
Experiment 1 (gold-label teacher, real embeddings) is done for Banking77 and CLINC150: naive selection misses its target in about 43-58% of draws (small margins); Bonferroni-certified selection holds violations far below delta at a cost of about 4-13 coverage points at 1,000-2,000 audit labels; my first certified gate had a power flaw (fixed, ADR 0004). (Later in the same day, margin baseline, Holm and across-split ranges were added; see 1d.)

## 1d. Results since 1c (2026-11-01; details in `docs/notes/exp1b-findings.md`, `exp2-findings.md`)
RQ4 (teacher noise) is now measured with a real LLM teacher (Claude Haiku 5.5, 76.5% / 90.9% agreement with gold): bounded gates still hold for teacher agreement; agreement does not certify correctness; a gold-trained student beat the teacher. RQ3 (shift) has a first study: rolling Holm on uniformly audited labels helps under mild shift, nothing recovers within 6,000 decisions under unseen-class shift at <= 10% audit; the anytime-valid alarm has no pre-shift false alarms but is slow. RQ5 (economics) has a closed-form break-even model (`src/cascade/economics.py`). **Still open:** TRACER's package on identical splits, a second teacher, more datasets/encoders, importance-weighted audits, alpha-spending over recalibrations, literature check.

## 2. Research questions and hypotheses
Define: teacher `T(x)` (LLM label), student `S(x)` with confidence `c(x)`, accepted set `A_t = {x: c(x) >= t}`. **Agreement risk** `R(t) = P(S(x) != T(x) | x in A_t)`. Also track **gold error** `P(S != y | accepted)` where human labels exist.

- **RQ1 (guarantee validity; reshaped, see 1b):** Compare naive selection, certify-once (TRACER-repo style, my reading of its changelog) and fixed-sequence certified selection on real teacher-labelled traces. Does choosing `t` with a distribution-free bound (Clopper-Pearson upper confidence bound + fixed-sequence testing, i.e., Learn-then-Test / conformal-risk-control style) keep `R(t) <= alpha` with probability `>= 1-delta` on fresh data, versus a naive "choose t on a held-out sample so empirical agreement >= alpha" gate (TRACER-style)? *H1:* the naive gate violates the target in a non-trivial fraction of calibration draws, especially with small calibration sets and under shift; the bounded gate rarely does, at the price of some coverage.
- **RQ2 (backend frontier):** Which cheap backends give the best cost-coverage frontier at a fixed alpha: TF-IDF+LR, frozen embeddings+LR/GBM, small fine-tuned encoder, a fast typed-decision model (Jev, if accessible), a small LLM? *H2:* frozen embeddings+LR wins on easy intent tasks and fails on NLI-like tasks, matching TRACER's refusal; a fine-tuned encoder extends coverage at higher training cost.
- **RQ3 (shift):** How fast does agreement degrade under (a) class-prior shift, (b) unseen classes (out-of-scope), (c) input perturbation (typos, code-mixing), (d) topic drift? Can online recalibration on a rolling audit sample plus retraining on escalations restore coverage, and how much does the audit sample cost? *H3:* the bounded gate with rolling recalibration holds the risk target; naive gates silently drift.
- **RQ4 (teacher noise):** Agreement with the teacher is not accuracy. How large is `P(T != y)` on gold-labelled sets, and how much does teacher ensembling/self-consistency/prompt variants reduce it? Does optimising agreement with a noisy teacher cap achievable gold accuracy? *H4:* the student can match but not exceed teacher accuracy; teacher error is a floor on gold error unless labels are cleaned.
- **RQ5 (economics):** Given prices, volume and audit rate, when does the cascade pay back its labelling + training + audit costs? Provide a closed-form break-even and a sensitivity analysis. *H5:* payback needs high volume of easy decisions; show the break-even curve instead of a headline percentage.
- **RQ6 (asymmetric costs, stretch):** For agent-action gating (see `../agentgate-bench/`), how should thresholds change when a false allow costs far more than a false block?

## 3. Experimental design
**Tasks (verify licences first; `../data-sources/datasets.csv`):** Banking77 (77 classes), CLINC150 (150 + out-of-scope), AG News (easy), GoEmotions (noisy), an NLI task (hard negative control). Optional: RideScore event windows, AgentGate Bench actions.
**Splits (three-way, fixed seeds):** train (student), calibration (choose threshold), audit/test (report). Never tune on audit/test. Repeat with 100 random calibration draws for RQ1.
**Teachers:** one cheap and one stronger current-generation LLM, structured output constrained to the label set (TRACER reports out-of-label outputs on 150 classes: handle with schema/enum-constrained decoding and a retry/fallback). Record exact model id, date and price per run. Check each provider's terms on using outputs for training (see `docs/06`).
**Students:** TF-IDF+LR; frozen embeddings (a small sentence-transformer, plus one API embedding) + LR and GBM; small fine-tuned encoder; Jev backend (optional); small LLM zero-shot as a baseline.
**Calibration:** raw softmax, temperature scaling, isotonic; report ECE and reliability diagrams.
**Gates compared:** (G0) fixed threshold; (G1) naive held-out agreement gate (TRACER-style); (G2) Clopper-Pearson bound with fixed-sequence testing; (G3) conformal risk control variant; (G4) learned deferral (Gupta-style features: confidence, entropy, margin, embedding).
**Procedure for G2:** sort thresholds from most to least confident; for each, let `n` be accepted calibration items and `k` the disagreements; compute the upper bound `U = Beta^{-1}(1-delta; k+1, n-k)`; accept the largest-coverage threshold such that all thresholds tested before it passed `U <= alpha` (fixed-sequence testing controls family-wise error). Validate empirically across draws.
**Metrics:** coverage (cheap share), agreement risk `R`, gold risk, violation rate of the guarantee (fraction of draws with `R > alpha`), cost per 1,000 decisions (tokens x price, logged), latency p50/p95/p99, ECE, risk-coverage AURC, break-even volume, retraining cost. Bootstrap 95% CIs; 5 seeds; report all runs including failures.
**Shift protocol (RQ3):** construct streams where the class prior changes, unseen classes appear, text is perturbed, and topics rotate; run rolling recalibration with audit rates 1%, 2%, 5%; plot risk and coverage over time.
**Controls:** LLM-only; majority class; student-only without a gate (to show the gate's value).

## 4. Budget (verify current prices; formula, not promises)
`teacher_cost = n_calls * (prompt_tokens * price_in + output_tokens * price_out)`. For 77-class and 150-class prompts the label list dominates prompt size (a thousand-plus tokens): use prompt caching where the provider supports it, batch where allowed, and cap sample sizes (start with 2,000-3,000 labelled items per task). Cache every teacher response to disk keyed by (model, prompt hash). Record real spend per experiment in `results/cost.csv`. Embeddings and logistic regression run on CPU; fine-tuning a small encoder may need a GPU or a short cloud rental: check your hardware first.

## 5. Build route (research and engineering interleaved; replaces the first 6 weeks of `docs/07-roadmap.md`)
| Days | Work | Output / gate |
|---|---|---|
| 1-2 | **DONE 2026-11-01:** repo scaffold (26 tests, 98% coverage, ruff + mypy strict), CI/Docker drafted, ADRs 0001-0003, TRACER paper + repo read, analysis written. **Remaining:** git init, Docker build check, read `tracer/fit/*` and `update`, Gupta et al. and conformal abstention in full | reading notes in `docs/notes/`, reproduction plan |
| 3-5 | Data loaders (licences recorded), constrained-output teacher harness with caching and cost logging, label-set validation | 2 tasks labelled by teacher; spend log; gold-vs-teacher agreement (RQ4 baseline) |
| 6-8 | Students (TF-IDF+LR, embeddings+LR), three-way splits, metrics library with tests | first risk-coverage plots; unit tests for metrics |
| 9-10 | Calibration (temperature, isotonic), ECE, reliability plots | calibration report |
| 11-14 | Gates G0-G3 on real traces + RQ1 simulation (100 calibration draws); scaffold already contains `select_naive`, `select_certified`, `certify_once` and the synthetic experiment | **headline experiment 1:** violation rates and coverage of naive vs certify-once vs certified selection on real tasks |
| 15-21 | Remaining tasks (CLINC150, AG News, GoEmotions, NLI), fine-tuned encoder, optional Jev backend | frontier plots across tasks; negative results documented |
| 22-28 | Shift streams + rolling recalibration (RQ3), teacher noise/ensembles (RQ4) | **experiments 2-3** |
| 29-35 | Economics model + break-even (RQ5); stretch: cost-sensitive gate for agent actions (RQ6) | break-even notebook; report draft |
| 36+ | Service build (gateway, SDKs, dashboard, infra) per `docs/07-roadmap.md` weeks 5-12 | production scorecard |

**Technical gates:** if experiment 1 shows no difference between naive and bounded gates, report that honestly and continue to the service. If the student cannot reach the agreement target on any task, publish the harness and the negative finding. Do not tune on test data.

## 6. Risks to validity (write them in the report)
Teacher is not ground truth; benchmarks are clean and small compared with production traffic; exchangeability assumption breaks under drift (the bound is marginal and holds only if calibration data resembles deployment data); multiple comparisons across thresholds; API model versions change over time; prompt sensitivity; label leakage between splits (duplicates/near-duplicates: dedupe); embedding model contamination with benchmark data; cost numbers depend on prices that change.

## 7. Reproducibility and writing
Pinned environment, seeds, dataset checksums, one command per experiment (`make exp1`), results as JSON + generated tables, raw teacher outputs cached and (if licences allow) published. Report outline: problem, related work (credit TRACER and others precisely), method, experiments, negative results, limitations, cost analysis, artifact link. Optional: arXiv-style PDF or a long blog post; do not claim novelty without a literature check.

## 8. Immediate next actions (this week)
1. Read TRACER's full paper and repo; write a one-page comparison (what they guarantee, what they measure, what they omit).
2. Read Gupta et al. and the conformal abstention paper; implement the Clopper-Pearson + fixed-sequence selection in a 30-line notebook on synthetic scores to see the coverage lost.
3. Verify licences for Banking77 and CLINC150 and record them.
4. Check your hardware (CPU/GPU) and decide the embedding model.
5. Pick the teacher(s), read their current output-use terms, and set a spend cap.
