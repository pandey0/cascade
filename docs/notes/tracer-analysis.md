# TRACER analysis: what it does, what it does not, and how Cascade can extend it

Date: 2026-11-01. Sources read this session: the full paper text (arXiv 2604.14531v1, 8 pages; local copy `papers/rida2026-tracer-arxiv-2604.14531.pdf`, gitignored) and the repository snapshot `github.com/adrida/tracer` (MIT, cloned depth 1: about 4,800 lines of Python under `src/` and 2,260 lines in 15 test files; I read the README, the CHANGELOG "Unreleased" section, `docs/system1.md`, and the relevant parts of `docs/api.md`, plus targeted greps over `src/` and `docs/`). I have **not** run the code or reproduced numbers. Items marked *(inferred)* are my reading, to be confirmed in code.

## 1. What TRACER is
A system that trains classical-ML "surrogates" on an LLM's own classification traces and serves them behind a gate, deferring uncertain inputs to the teacher.
- **Problem (paper section 3.1):** teacher `T`, surrogate `f`, acceptor `a(x) in [0,1]`, hybrid `h(x) = f(x)` if `a(x) >= tau` else `T(x)`. Maximise coverage subject to teacher agreement `TA = P[f = T | accepted] >= alpha`.
- **Surrogates (3.2):** precomputed embeddings (BGE-large-en-v1.5, 1024 dims) + a pool of logistic regression, SGD linear, MLP, decision tree, random forest, extra-trees; best by teacher-label macro-F1 on validation.
- **Acceptor:** a logistic regression over four confidence features of the surrogate's probability vector (top-1, top-2, margin, normalised entropy). `tau` is chosen by sweeping all unique acceptor scores on a held-out split to maximise coverage with `TA >= alpha`.
- **Pipelines:** *Global* (no gating; allowed only if overall TA already >= alpha) vs *L2D* (surrogate + acceptor); a residual two-stage cascade exists in code but was never selected.
- **Parity gate (3.3):** candidate must clear `TA >= alpha` on a held-out shadow split (not used for training or threshold calibration) and a 5% coverage floor; otherwise fall back to teacher-only. Temporal: may pass later with more traces.
- **Flywheel (3.4):** day 1 everything goes to the teacher; each `update()` merges new traces and **refits from scratch**.
- **Artifacts (3.5):** slice summaries, representative example cards, contrastive boundary pairs, temporal deltas, disagreement cards.

## 2. Reported results (paper; teacher Sonnet 4.6, cached outputs, 5 daily batches)
| Task | Teacher accuracy vs gold | Outcome |
|---|---|---|
| Banking77 (77 classes; 10,003 train / 3,080 test) | 78.7% train / 81.0% test | alpha .80-.85: 100% coverage (TA .894); .90: 96.1% (TA .912); .95: 83.2% (TA .959); GT accuracy .804-.816 |
| CLINC150 (18,000 / 4,500) | 94.4% / 93.1%; 7 spurious labels -> 157 effective classes | 100% coverage at all alpha; at alpha .95 test TA = **.930 < .95** although calibration TA was .952 (the paper flags this cal-test gap) |
| MNLI (negative control, ground-truth labels as teacher; 2k/5k/10k) | n/a | 0% coverage in all 9 configs: gate refuses (frozen embeddings cannot separate NLI) |
Baseline: one logistic regression trained on all traces at once with a confidence threshold (hindsight baseline); at Banking77 alpha .95 it reaches 87.8% coverage vs TRACER's 83.2% (TA .951 vs .959). Flywheel on Banking77 at alpha .95: coverage 73.4% (2,001 traces) -> 83.4% (day 4) -> 82.6% (day 5). Cost projection: about $2.60 per 1,000 teacher calls; at 10K queries/day an 83% reduction at 83.2% coverage (arithmetic projection, not a measured bill).

## 3. The repository is ahead of the preprint (snapshot "Unreleased" changelog)
- **Final certification:** new fits reserve **20%** of rows (`certification_fraction`), `certification_alpha=0.10`; the selected serving policy (including its OOD guard) is checked **once** with a **one-sided Clopper-Pearson lower bound** on agreement; "never retry other candidates"; zero accepted examples cannot certify; small fits may decline deployment. The changelog states the statement requires independent representative examples and does **not** cover distribution shift, correlated sessions, or adaptive reuse.
- **OOD guard:** distance-based; overrides acceptance; reported as `deferred`.
- **Transactional fit/update**, hardened server (127.0.0.1 default), watcher for trace capture (Python and JS), Python >= 3.12, MIT, tests (15 files, about 2,260 lines).
- Hosted-app telemetry/CLI **removed** from the OSS code.
- docs/system1.md: the teacher "can be an LLM, a foundation model built for System 1 decisions, or another classifier" (no concrete Jev integration in what I read).

**Code check (2026-11-01):** `src/tracer/fit/certification.py` confirms the design: `certify_policy` evaluates exactly one fixed policy (including its OOD filter) on reserved, untouched rows and marks it `certified` iff the one-sided Clopper-Pearson **lower** bound on teacher agreement is >= the target at confidence parameter `alpha` (their naming); no retries; its docstring states the statement does not cover shift, dependent sessions or repeated adaptive reuse. This matches the `certify_once` gate in `cascade.gates`. Not yet read: `fit/pipeline.py` (how the candidate policy is selected before certification).

## 4. What I could not find in this snapshot (grep and reading; verify before claiming)
No built-in **audit sampler for accepted traffic** after deployment (the docs only advise including representative traffic); no importance weighting; no **sequential / anytime-valid monitoring** of agreement under drift; no shadow/canary mode; no cost/break-even model beyond the paper's arithmetic; no teacher-noise-aware (gold-risk) guarantee; no encoder fine-tuning; no multi-tier cascade; no OpenAI-compatible gateway / multi-tenant service.

## 5. Weaknesses and open issues (some stated by the paper)
1. **Cal-test gap** (CLINC150 .952 -> .930): the gate is only as strong as calibration representativeness. Partly addressed in the repo by one-shot certification, which is valid but all-or-nothing.
2. **Selection by empirical sweep** is optimistic: thresholds are picked at the edge of the target on the same data, so about half of selections miss the target by construction (my experiment 0 shows 44-55% violation on synthetic scores, small magnitude).
3. **Teacher is not truth:** Banking77 teacher accuracy 81.0% means 100%-agreement surrogates inherit ~19% error; CLINC150 surrogate reproduces 7 spurious labels.
4. **Flywheel label censoring:** in the paper's protocol the five "daily batches" are fully teacher-labelled *(my reading of section 4.1)*; in real deployment, accepted requests receive no teacher label, so refits and calibration see only deferred (selection-biased) traces unless accepted items are randomly audited. The repo docs (`docs/api.md`, `update()`) do warn: "Include representative traffic rather than only old-policy deferrals", but I found no built-in sampler, weighting or guarantee for doing so: the burden is left to the user.
5. **Baselines are weak** (single hindsight LR threshold); the paper lists RouteLLM and distillation comparisons as planned.
6. **Encoder is frozen** (BGE-large); tasks needing compositional reasoning (NLI) are refused; the paper proposes encoder fine-tuning as future work.
7. **Refit from scratch** each update (paper lists incremental fitting as future work).
8. No user study of artifacts.

## 6. Extension candidates (ranked for Cascade)
| # | Idea | Why it is a real addition | Evidence needed | Cost |
|---|---|---|---|---|
| E1 | **Certified threshold selection** (fixed-sequence testing over a fixed grid; Learn-then-Test style) instead of select-then-certify-once | keeps validity while recovering coverage; avoids "decline everything if the single check fails" | exp0 (done, synthetic) -> real tasks | low |
| E2 | **Audit sampling + importance weighting** for post-deployment agreement estimation; quantify the bias of refits trained on deferred-only traces | turns TRACER's advice into a mechanism with a statistical guarantee; defines the audit-cost vs guarantee trade-off | simulation on Banking77/CLINC150, then real traces | low-medium |
| E3 | **Anytime-valid monitoring** (confidence sequences / e-processes) of agreement on audited accepted traffic with automatic fallback | answers "does not cover distribution shift"; production-relevant | shift streams (prior, unseen class, perturbation, language) | medium |
| E4 | **Teacher-noise-aware risk:** estimate teacher error with a small gold audit; report bounds on gold risk, not only agreement; teacher ensembles/self-consistency | directly addresses 81% teacher accuracy | Banking77/CLINC150 gold labels | low-medium |
| E5 | **Encoder fine-tuning behind the gate** to flip tasks like NLI from refuse to deploy (small encoder, Colab GPU) | the paper's own future-work item; measurable outcome | MNLI + teacher traces | medium (GPU) |
| E6 | **Three-tier cascade** (embeddings+LR -> open typed-decision model -> frontier LLM) with per-tier certification and a cost model | uses System-1 models (Jev or an open reproduction) as a middle tier | cost/accuracy frontier on 3 tasks | medium |
| E7 | **Cost model + break-even** including labelling, audits, retraining | paper only projects | closed form + sensitivity | low |
| E8 | **Cross-lingual / code-mixed shift** (Hindi, Kannada, Hinglish) as a shift axis for OOD guard and certificate | uses your language edge without touching IndicRAG; MASSIVE lists many languages (verify the languages and licence) | embedding + guard under language shift | medium |
| E9 | **Service engineering:** OpenAI-compatible gateway, shadow/canary, multi-tenancy, observability, IaC | production-grade deliverable TRACER's OSS dropped | scorecard | high but core to the project |
| E10 | **Upstream contribution:** propose E1/E2 to TRACER as a PR or issue (MIT) | real OSS exposure, credit and review | agreement with maintainer | low |

## 7. Recommended scope
Research core = **E1 + E2 + E3 + E4** (a coherent story: certify, audit, monitor, account for teacher noise), with **E7** and optional **E5/E6**. Engineering core = **E9**. Position the write-up as: "TRACER-style trace distillation with certified selection and continuous certification under drift", crediting TRACER precisely. Do not claim novelty before a proper literature check beyond the sources above.

## 8. Immediate actions
1. Pin the TRACER commit you compare against (`git rev-parse HEAD` in the clone) and record it in `results/`.
2. Read `src/tracer/fit/` (`pipeline.py`, `certification.py`) and `update` to confirm items 4 and the "not found" list.
3. Reproduce a Banking77 baseline with cached teacher labels using TRACER's own package (Colab or local CPU), then run E1/E2 against it.
4. Decide with the maintainer (issue) whether E1/E2 belong upstream.
