# 04 Evaluation plan (this is the product's credibility)

## Benchmark suite
- Text decisions: public intent/topic/emotion datasets (see `../../data-sources/datasets.csv`; verify licences): Banking77-style many-class, CLINC150-style out-of-scope, AG News-style easy, GoEmotions-style noisy.
- Domain tasks you control: triage on synthetic/consented data only; loopeng/agent tool-call gating.
- Streaming/sensor decisions: RideScore event windows (see `../../ridescore/`).

## Baselines
Teacher-only; small-LLM-only; embeddings+classifier only; RouteLLM-style strong/weak routing (if applicable); majority/threshold; Jev-style typed decision model (if accessible).

## Metrics
Agreement with teacher and accuracy vs gold (when gold exists); **selective risk-coverage curve**; ECE and reliability diagrams; cost per 1,000 decisions (tokens x price, recorded at run time); latency p50/p95; savings at target agreement; cold-start cost to train; time-to-break-even; robustness to drift/perturbation; escalation rate over time (should fall).

## Method
Fixed seeds; train/calibration/test split with a time-based split where possible; bootstrap CIs; report every config; record exact model versions and prices per run; publish scripts; keep a "negative results" section.

## Success bar for a public claim
Savings >= X% at agreement >= Y% on at least 3 tasks with CIs, plus a shadow-mode run on your own sample traffic (synthetic or public).
