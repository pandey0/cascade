# Does Cascade really help? A critique

Written 2026-11-02 after the v0.1.0 release, deliberately adversarial: from the point of view of an architect, an AI engineer and an application developer, plus what outside research says. Every number is either from this repo (with its source) or marked as an assumption. Where I found nothing, I say so.

## Verdict

**It helps in a narrow regime, and not for most teams.** The cost story is much weaker than the README first made it sound; the strongest real value is something else (see below). **Update (same day): that hole is now filled** by experiment 3 ([notes/comparison-findings.md](notes/comparison-findings.md)). It confirms the worst of this critique: when human labels are available, a plain small model beats both the LLM and Cascade on accuracy and, above roughly 100,000 requests/day, on cost.

| Claim | Holds? |
|---|---|
| "Saves money on LLM calls" | **Only at high volume.** With a cheap LLM, savings cover just the hosting at roughly 75,000 requests/day (about 780,000/day if prompt caching makes the LLM 10x cheaper), and repaying engineering time takes about 1 million/day. See the economics below. |
| "Faster: milliseconds instead of an LLM round trip" | **Median yes, tail no.** Audits run inside the request, so the audited share of requests pays the full LLM latency (measured: 5% audit rate -> p95 = 306 ms with a 300 ms LLM). |
| "A statistical guarantee on errors" | **Yes, but of a narrower kind than it sounds:** agreement with the LLM, under an i.i.d. assumption, per recalibration. Not correctness, and not under arbitrary drift. |
| "Keeps working as traffic changes" | **Partly.** It notices and can withdraw; it does not learn. Severe shifts were not recovered in our experiments. |
| "Production-ready" | **No.** v0.1.0 alpha with the architectural gaps below. |

**Where the real value is:** (1) a *governance-grade, auditable* statement of how often the cheap path disagrees with the reference, plus monitoring that tells you when that stops being true: most teams doing this do it ad hoc; (2) decoupling the common path from the LLM provider's latency and outages, which matters when rate limits or availability bind rather than price. Cost savings are the weakest of the three motivations unless you are at very large scale.

## What outside research says (and does not say)

| Finding | Source | Consequence for Cascade |
|---|---|---|
| A 22M-parameter SetFit model reached 91.1% accuracy at about 2-5 ms on the MASSIVE intent benchmark vs 68.8% at about 3.4 s for a zero-shot LLM (the paper's few-shot LLM figures are estimates from the literature) | [arXiv 2602.18922](https://arxiv.org/pdf/2602.18922) | **The main competitor is not "the LLM", it is a small model fine-tuned on a few hundred labelled examples.** For stable label sets that is simpler and often better. Cascade's student is a weaker baseline (frozen embeddings + logistic regression). |
| LLM-labelled distillation into a small model is an established workflow needing roughly 50-100 examples for SetFit | [sieves.ai distillation guide](https://sieves.ai/guides/distillation/) (tooling guide, not a study) | The "learn from the LLM" half of Cascade is not new or hard; the certification and monitoring are the added part. |
| Students can sometimes *beat* a noisy LLM teacher | [arXiv 2312.10185](https://arxiv.org/pdf/2312.10185) (two datasets, low-data) | Our result is mixed: on Banking77 the student trained on the LLM's labels agreed with the dataset labels 72-74% vs the LLM's 75-77%, i.e. no denoising; a student trained on the dataset labels reached 92%. |
| Selective-classification risk guarantees hold on i.i.d. data but degrade under distribution shift; guarantees under unknown shift are an open problem | [arXiv 2405.05160](https://arxiv.org/html/2405.05160v2), [NeurIPS 2023 talk](https://neurips.cc/virtual/2023/80532) | Matches what we measured (unseen classes defeat re-certification). Confidence from softmax-style scores is fragile off-distribution. |
| Cascades/routers can cut cost a lot (FrugalGPT reports up to 98%), but need training data from the same distribution and enough volume to repay it | [arXiv 2305.05176](https://arxiv.org/pdf/2305.05176) | Headline savings depend on the price gap and volume; claims in this area have also been criticised as inflated by evaluation artefacts (2026 preprints; I did not verify which). |
| Semantic caching is another way to avoid repeat LLM calls; the threshold trades hit rate against silent wrong answers | [GPTCache docs](https://gpt-cache-test.readthedocs.io/en/latest/index.html) and vendor guides | An unevaluated alternative for exactly our "repetitive requests" case. |

**Not found:** any study of long-term production outcomes (drift, label upkeep) for LLM-to-small-model cascades, any head-to-head of a certified cascade vs fine-tuning vs caching vs a cheaper LLM, and current price-trend data (that search returned nothing; my price figures come from our own measurement and Anthropic's published price table).

## The economics, with hosting and engineering time

Reproduce with `python scripts/make_economics.py` (`results/economics.md`, `src/cascade/economics.py`).

Assumptions (not measurements unless stated): LLM cost per call $0.000204 (**measured**, Claude Haiku 5.5, 77-label prompt, no caching) or $0.00002 (**illustration** assuming prompt caching at ~10% of the input price; unverified for this model); the student serves ~50 requests/s per node (**measured** 30-70 on 4 pinned cores); node cost $0.15/hour (**assumed**); two replicas always on ($7.2/day); 50% answered cheaply; 5% audited; $10,000 of engineering to adopt.

| LLM cost per call | Daily volume where savings just cover hosting | Payback of $10k at 100k/day | at 1M/day | at 10M/day |
|---|---|---|---|---|
| $0.000204 (no caching) | ~75,000 | ~4,080 days | ~112 days | ~10 days |
| $0.00002 (with caching) | ~776,000 | never | ~4,800 days | ~117 days |

My earlier README line "break-even after 5,000-12,500 requests" counted only the labelling cost and was misleading as a headline. **Under ~100,000 requests/day with an inexpensive LLM, Cascade does not pay for itself.** The case gets better with a pricier teacher model, a longer prompt, or far more volume.

## As an architect

What is good: clear separation (student / gate / teacher / audit store), fail-safe defaults (gate withdraws; fail-open or fail-closed is explicit), observability and runbooks, a deployment that was actually exercised.

What would worry me, with evidence:

1. **State is per replica.** The audit database is SQLite on an `emptyDir`; the threshold, drift monitor and rate limiter live in each pod's memory. Two replicas calibrate independently, can serve different cutoffs, and lose audit history on restart. Scaling out breaks the statistical story. Needs a shared store (Postgres or Redis) and a single owner for recalibration.
2. **Audits sit in the request path (measured).** An audited request waits for the LLM even though the answer is already known. Test: 400 cheap-path requests, 5% audit rate, 300 ms LLM -> p50 0 ms but p95 306 ms. Fix: queue audits and run them in the background, dropping when the queue is full.
3. **The LLM-call thread pool can be exhausted (measured).** 8 workers serve LLM calls; a timeout abandons the wait but not the call. With a stalled LLM (3 s calls, 0.5 s timeout) and then recovery, requests kept timing out for ~2.5 s afterwards because stuck calls still held the workers. With real provider timeouts of tens of seconds, recovery lag is tens of seconds. Fix: enforce the timeout inside the HTTP client and size or bound the pool deliberately.
4. **"Cheap" is relative.** The student needs a PyTorch encoder: ~0.8 GB resident memory and 12-25 ms CPU per request, 9 s start-up. A hashing embedder avoids PyTorch but is weaker (83% vs 92% on Banking77 in our demo artifact).
5. **Artifact and config distribution** use a ConfigMap (1 MB limit) and environment variables; there is no versioned rollout (canary a new student or cutoff), though shadow mode exists.
6. **Complexity budget:** new moving parts (artifact, audit store, monitors, a service) for a saving that is small unless volume is large.

## As an AI engineer

1. **The promise is conditional.** It bounds disagreement with the LLM, assuming the audited sample resembles current traffic. We measured that agreement is neither sufficient nor necessary for correctness (a certified student still missed a correctness target in 70% of draws on Banking77 at alpha 0.10).
2. **Power costs coverage.** At alpha 5% and 2,000 audited examples the certified gate answered 27% of requests cheaply vs 49% for the naive one (quickstart), and declined to deploy 14% of the time. With few labels it may never certify.
3. **Weak student.** Frozen MiniLM embeddings + logistic regression. A fine-tuned encoder or SetFit would likely cover more at the same risk. We never tested one.
4. **Confidence is fragile off-distribution.** Unseen classes got high-confidence wrong answers; re-certification and the alarm recovered only partly or late. No out-of-distribution guard (TRACER has one).
5. **Statistics not finished.** Each recalibration has its own failure probability; over many recalibrations the family-wise error is not controlled (no alpha-spending). One global alpha, no per-class risk (hard classes can hide behind a good average).
6. **No learning loop.** The student never improves: inputs are stored only as hashes, so there is nothing to retrain on. (An earlier doc sentence described a "flywheel"; that was wrong and is corrected.)
7. **The teacher moves.** A provider model update changes the reference silently. Labels are cached by model id, but nothing re-validates the student when the teacher changes.
8. **Thin evidence:** two datasets, one student, one LLM, 3-5 splits, constructed drift. The missing experiment is the important one: compare against fine-tuning on a few hundred human labels, a cheaper LLM with prompt caching, and a semantic cache.

## As an application developer

Good: typed, tested (98 tests, 93% coverage), CI, an OpenAPI spec, a runbook, a quickstart that works from a clean install.

Friction: no SDK and no OpenAI-compatible endpoint (the API is bespoke); Python only; training and certification are research scripts you adapt, not a single command; PyTorch is a heavy dependency for the "cheap" path; configuration by environment variables; the model artifact format is unversioned; the demo and load tests never talk to a real LLM.

## Research value

Certified threshold selection is not new (Geifman and El-Yaniv 2017; Learn-then-Test), the cascade idea is TRACER's, and the monitoring method is existing work. What remains is modest: an empirical comparison of selection methods in the LLM-distillation setting, a measured demonstration that agreement with a noisy teacher is not correctness, and a small drift study. That is a fair technical report or portfolio project, thin for a main-track paper. See [notes/literature-check.md](notes/literature-check.md).

## What would make it really help (in priority order)

1. **Let the guarantee target the truth, not only the LLM (new top priority, from experiment 3):** a small human-labelled audit mode. Today a student that is *better* than the LLM is throttled by agreement with it (Banking77: 89.5% accurate, allowed to answer 5% of requests at a 10% target). The earlier comparison item is done: [notes/comparison-findings.md](notes/comparison-findings.md).
2. **Ship a cost calculator** (volume, prices, hosting, engineering) that tells a team in one minute whether Cascade is worth it; the model exists in `economics.py`.
3. **Fix the two measured defects:** background audits; bounded, client-enforced teacher timeouts.
4. **Shared state** for multi-replica deployments.
5. **A gold-audit mode:** certify true accuracy from a small human-labelled audit, not just agreement.
6. **Out-of-distribution guard and per-class risk**, then an opt-in retraining loop.
7. **Adoption surface:** OpenAI-compatible endpoint, a thin SDK, a one-command build.
8. **Alpha-spending** across recalibrations.

## Corrections made because of this review
- `docs/story.md` no longer claims a retraining "flywheel"; it states that the student is not retrained.
- The README cost row and "not a good fit" table now include hosting and engineering time instead of the labelling-only break-even.
- `economics.py` gained `break_even_daily_volume` and `payback_days` (with tests) and the script now prints the hosting-aware table.

## Update after experiment 3 (head-to-head comparison)
- **Confirmed:** a small model on 500-3,000 human labels beats the LLM's accuracy and, from about 100,000 requests/day, costs far less (year-1 on Banking77 at 1M/day: $8,032 vs $74,482).
- **Where Cascade still earns its place:** when the LLM's answers are the only labels (about half the LLM calls at a 10% target for under a point of accuracy) and when you need an auditable, monitored bound. A semantic cache gets a similar call reduction with less machinery but no bound.
- **New weakness found:** agreement-based certification throttles a student that is better than the LLM, and an LLM fallback can *lower* end-to-end accuracy (CLINC150: 94.3% with fallback vs 95.0% for the student alone).
- **Still untested:** prompt caching (needs an API key), a stronger fine-tuned small model, latency under load with a real LLM.
