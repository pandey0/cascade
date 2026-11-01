# Findings: does Cascade beat the alternatives? (experiment 3)

Plan and expectations were written first: [comparison-plan.md](comparison-plan.md). Code: `scripts/compare_approaches.py`
(results in `results/compare_*.json`, run record in `evidence/`) and `scripts/summarize_compare.py`
(`results/compare_summary.md`, figures 7 and 8). No API calls were needed: it reuses the 4,000 Claude Haiku 5.5 labels
from experiment 1b. Three data splits, pools of about 1,000 held-out messages, cutoff certified on 400 audited examples
(100 draws), accuracy always against the dataset's labels. LLM-only accuracy: **75.8%** (Banking77), **91.0%** (CLINC150).

## Results against the expectations

| Expectation (written beforehand) | Verdict | Evidence |
|---|---|---|
| **E1.** A few hundred human labels suffice for a small model to match the LLM; if so, Cascade is dominated when human labels exist | **Confirmed, with the label counts.** | Banking77: 500 labels give 74.2% (about the LLM's 75.8%), 1,000 give 84.4%, 5,000 give 90.9%. CLINC150 (150 categories) needs more: 1,000 give 86.2%, **3,000 give 95.0% vs the LLM's 91.0%**. Fig. 7. |
| **E2.** Cascade only makes sense when the LLM's answers are the only labels | **Mostly confirmed, with a surprise about the target.** | Trained on 1,000 LLM labels at a 10% error target, Cascade answers 53% (Banking77) and 46% (CLINC150) of requests cheaply with **no loss on Banking77 (75.8% vs 75.8%) and 0.7 points on CLINC150 (90.3% vs 91.0%)**. At a 5% target it almost never deploys at these sample sizes (coverage 3-9%). |
| **E3.** A semantic cache gives modest hit rates and silent errors | **Wrong in part.** Hit rates were higher than I expected on Banking77. | Banking77, similarity 0.85: 45% of requests served from the cache for a 0.6-point accuracy loss (0.90: 26%, -0.4 points). CLINC150 is lower (0.85: 22%, -0.1 points). Accuracy on cache hits was 82-84% on Banking77, not worse than the LLM's own 75.8%: the "silent errors" are mostly the LLM's own errors copied. Fig. 8. |
| **E4.** Prompt caching moves break-even volumes up several times | **Not tested.** The probe needs an API key; the key in `.env` was invalid (rotated). Stays an assumption. | `scripts/caching_probe.py` is ready. |

## What the numbers say, in plain words

1. **If you can get human labels, skip the cascade.** A small model on 500-3,000 human labels beat the LLM's accuracy on both datasets, needs no LLM at serving time, and in the cost model is the cheapest option from about 100,000 requests a day (Banking77, year 1: $8,032 vs $74,482 for the LLM alone at 1 million/day). Its weakness is that it comes with no guarantee, no fallback and no drift alarm.
2. **If the LLM's answers are all you have**, Cascade works as designed at a looser target: about half the LLM calls, almost no accuracy loss. But a semantic cache gets a similar reduction (Banking77) with far less machinery, no training and no guarantee. Cascade's extra is the *measured, auditable* error bound and the monitoring.
3. **Certifying against the LLM backfires when the small model is better than the LLM.** With 3,000 human labels the Banking77 student scores 89.5% alone, yet the certified gate lets it answer only 5% of requests, because it must agree with an LLM that is wrong a quarter of the time. On CLINC150 the Cascade with an LLM fallback ends *below* the small model alone (94.3% vs 95.0%), because the fallback is the weaker answerer. **The guarantee should be able to target the dataset's truth (a small human-labelled audit), not only the LLM.** This is now the highest-priority product change.
4. **The 5% target is hard with realistic audits.** With 400 audited examples the certified gate rarely deploys at a 5% target; the "about half" coverage in the quickstart needed 2,000.

## Cost model (all non-LLM numbers are assumptions)
Human label $0.10; two always-on nodes at $0.15/hour; small-model serving $8e-7/request; one-off engineering $5,000 (small model), $10,000 (Cascade), $3,000 (cache). LLM price per call is measured. Year-1 cost, including one-off costs:

| Banking77 | accuracy | LLM calls | 10k/day | 100k/day | 1M/day | 10M/day |
|---|---|---|---|---|---|---|
| LLM only | 75.8% | 1.00 | $745 | $7,448 | $74,482 | $744,823 |
| Small model, 1,000 human labels | 84.4% | 0 | $7,731 | $7,758 | $8,032 | $10,770 |
| Cascade, 1,000 LLM labels, target 10% | 75.8% | 0.49 | $12,999 | $16,332 | $49,670 | $383,043 |
| Semantic cache, similarity 0.85 | 75.2% | 0.55 | $6,043 | $9,775 | $47,096 | $420,309 |

Full tables for both datasets: `results/compare_summary.md`. Below about 100,000 requests a day with an inexpensive LLM, **the LLM alone is the cheapest option**.

## Decision guide from this evidence
| Your situation | Best measured option |
|---|---|
| Under ~100,000 requests/day, inexpensive LLM | LLM only |
| You can get 500-3,000 human labels | Train the small model directly (more accurate and cheaper above ~100k/day); add monitoring |
| Only LLM answers exist, high volume | A semantic cache or Cascade; both cut LLM calls by roughly 20-50% for under a point of accuracy in these runs; Cascade adds the audited bound |
| You need an auditable, monitored error bound | Cascade (nothing else here gives one), ideally with a human-labelled audit |

## Caveats
One LLM (Haiku 5.5), two public datasets, one student type (a stronger fine-tuned model would raise the human-label curve), three splits, a cache seeded with only 1,000 earlier messages (real caches grow, so hit rates would rise), assumed costs, no latency measurement beyond the encoder and teacher timings already recorded, and accuracy measured against dataset labels, which have their own errors.
