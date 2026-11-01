# Plan: does Cascade beat the alternatives? (written BEFORE running)

Question: for a closed-set classification decision, which approach gives the best accuracy-vs-cost
trade-off, and at what daily volume does each win? This is the comparison `docs/critique.md` says is missing.

## Approaches compared (per dataset: Banking77, CLINC150; accuracy always measured against the dataset's labels)
| # | Approach | How it is evaluated |
|---|---|---|
| 1 | **LLM only** (Claude Haiku 5.5, zero-shot) | measured: its answers on the 2,000-message labelled sample per dataset |
| 2 | **LLM with prompt caching** | a small real probe (about 20 calls) measures the actual cached-token billing; price only, accuracy as #1 |
| 3 | **Small model on N human labels, no LLM** | logistic regression on frozen sentence embeddings, N in {50, 100, 200, 500, 1000, 3000} dataset labels, accuracy on held-out messages |
| 4 | **Small model on N LLM labels, no LLM at serving** | same model trained on the LLM's answers (N up to 1000) |
| 5 | **Cascade** = #3 or #4 plus the certified cutoff and LLM fallback | end-to-end accuracy = student where it answers, LLM elsewhere; cutoff certified on 400 audited examples (Holm, delta 0.1, alpha 0.05 and 0.10); averaged over 100 audit draws and 3 data splits |
| 6 | **Semantic cache** | reuse the stored LLM answer when a new message's embedding is within similarity tau of an earlier message; tau swept; seeded with 1,000 earlier LLM-labelled messages |

## Costs and volume model
Per-request LLM price: measured. Everything else is an **assumption, stated in the output**: human label
$0.10 each; hosting $0.15/hour per node, 2 nodes for any self-hosted approach; engineering one-off costs
(LLM only $0; prompt caching $500; semantic cache $3,000; small model on human labels $5,000; Cascade $10,000);
costs amortised over 12 months; volumes 10k, 100k, 1M, 10M requests/day. Accuracy and cost are reported
together because the approaches do not have the same accuracy.

## Expectations, recorded before seeing results
- **E1.** With a few hundred human labels, a plain small model matches or beats the LLM-only accuracy on Banking77 (we already saw 92% vs 76.5% with ~11k labels; the open question is how few labels suffice). If so, **Cascade is dominated whenever human labels exist.**
- **E2.** Cascade only makes sense when the LLM's answers are the only labels you have, or when the LLM's behaviour *is* the specification.
- **E3.** A semantic cache gives modest hit rates on diverse categories at safe thresholds, and its wrong answers are silent.
- **E4.** Prompt caching moves break-even volumes up several times.

## What would change my mind
- If the small model needs thousands of human labels to beat the LLM, Cascade-from-LLM-labels is more competitive than expected.
- If the semantic cache reaches high hit rates at high accuracy, it dominates Cascade for repetitive traffic.
- If prompt caching does not engage for this prompt size, the cheap-LLM baseline is more expensive than assumed.

## Limits fixed in advance
One LLM (Haiku 5.5), two datasets, one student type, 3 splits; hosting, label and engineering costs are assumptions;
no real traffic; no latency measurement beyond the encoder timings and the teacher timings already recorded.

## Outcome (added after the run)
Results and the verdict on each expectation are in [comparison-findings.md](comparison-findings.md). E1 confirmed (with label counts), E2 mostly confirmed, E3 partly wrong, E4 not tested (invalid API key).
