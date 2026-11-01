# Experiments 0 and 1a: how often do threshold-selection gates miss their target, and what does validity cost?

Date: 2026-11-01 (second full run: 8 gates, 5 splits per task). Code: `src/cascade/{gates,sim,bench,provenance}.py`, `scripts/run_all.sh` (one command reproduces everything). Raw tables/JSON: `../../results/`; generated summary: `../../results/SUMMARY.md`; figures: `../../paper/figures/` (provenance in `PROVENANCE.md`); run manifests: `../../evidence/`. The earlier 5-gate, 3-split run is kept in `results/archive_v1_5methods_3splits/`.

## Setup (and its limits)
- **Real data:** Banking77 (PolyAI/banking77, CC-BY-4.0 per its HF card) and CLINC150 in-scope (clinc/clinc_oos "plus", CC-BY-3.0 per HF card; out-of-scope removed). Frozen `all-MiniLM-L6-v2` embeddings; multinomial logistic regression student; confidence = max softmax probability; no temperature scaling. **Teacher = gold labels**, so "agreement" is accuracy; teacher noise is not modelled.
- **Pools:** for each of 5 random splits (duplicate texts kept together) half the data trains the student and the other half is the **pool**: accuracy 91.8-92.3% (Banking77), 96.5-96.8% (CLINC150). The pool is the finite population, so true risk and coverage of every threshold are exact. Calibration sets of size m are drawn from it without replacement, 400 draws per cell per split; headline numbers are means over splits, and figures show min-max across the 5 splits.
- **Gates** (accept if confidence >= threshold; delta = 0.10): `naive` (lowest threshold with empirical risk <= alpha on the calibration sample); `safety80` (naive against 0.8 alpha); `wilson` (lowest threshold whose one-sided Wilson upper bound <= alpha, **no multiplicity correction**); `certify_once` (naive on 80%, one Clopper-Pearson check on 20%, no retry; my reading of TRACER's final certification, not its code); `strict_sequence` (fixed-sequence from the strictest threshold); `bonferroni` (32 fixed grid points, each at delta/32); `holm` (Holm step-down over the same grid); `split_sequence` (40% picks a safe start, fixed-sequence on the rest).
- **Synthetic runs:** scores ~ Beta(8, 1.2), agreement probability min(0.999, 0.55 + 0.45 c^2).

## Results (violation = share of draws whose chosen threshold has true risk > target; coverage = share of traffic accepted, 0 if not deployed)
| task, target | m | naive viol / cov | wilson viol / cov | holm viol / cov |
|---|---|---|---|---|
| Banking77, 0.05 | 500 | 0.536 / 0.940 | 0.102 / 0.899 | 0.005 / 0.828 |
| Banking77, 0.05 | 1000 | 0.499 / 0.939 | 0.076 / 0.911 | 0.001 / 0.872 |
| Banking77, 0.05 | 2000 | 0.477 / 0.939 | 0.054 / 0.920 | 0.001 / 0.895 |
| Banking77, 0.03 | 500 | 0.540 / 0.871 | 0.088 / 0.807 | 0.001 / 0.494 |
| Banking77, 0.03 | 1000 | 0.500 / 0.868 | 0.074 / 0.829 | 0.001 / 0.749 |
| Banking77, 0.03 | 2000 | 0.474 / 0.868 | 0.045 / 0.841 | 0.000 / 0.802 |
| CLINC150, 0.02 | 500 | 0.499 / 0.966 | 0.079 / 0.931 | 0.003 / 0.636 |
| CLINC150, 0.02 | 1000 | 0.526 / 0.967 | 0.068 / 0.944 | 0.002 / 0.903 |
| CLINC150, 0.02 | 2000 | 0.450 / 0.966 | 0.060 / 0.951 | 0.002 / 0.930 |
All gates and the synthetic runs: `results/SUMMARY.md`, Figs. 1-2.

## What I conclude (and what I do not)
1. **Naive selection misses its target in roughly 45-54% of draws** at every size, because it picks the threshold where the empirical risk crosses the target. The misses are small (mean true risk of deployed naive policies was within about 0.003 of the target in the real-data runs).
2. **Bonferroni and Holm are valid and very conservative:** observed violation 0-0.5% against an allowed 10%. **Holm adds at most about one coverage point over Bonferroni** on these tasks (0.3-1.0 points), so the extra machinery buys little here.
3. **Relative to naive, validity costs coverage:** about 6.6 points (Banking77 0.05, m=1000) falling to 4.4 at m=2000; about 11.9 and 6.6 at target 0.03; about 6.4 and 3.6 on CLINC150 at 0.02. **At small m the cost can be large** (CLINC150 at m=500: 0.966 to 0.636). The synthetic task, whose risk hovers near the target, costs far more (26 points at target 0.05, m=3000).
4. **An uncorrected Wilson margin is an empirically strong heuristic on these tasks:** its violation rate was at or below about 0.10 in nearly every cell (0.045-0.102 at m >= 500; 0.12 at CLINC150 m=250) while keeping coverage within roughly 2-8 points of the corrected gates for m >= 1000. It has **no guarantee** (it still searches many thresholds on one sample), and the data here are i.i.d. and benign. So: if a formal guarantee is not required, a Wilson margin is a cheap and large improvement over naive; if one is required (audits, regulation, shifting traffic), use Holm/Bonferroni and pay the coverage.
5. **`safety80` depends on m:** violation 0.17/0.06/0.01 at m=500/1000/2000 (Banking77 0.05), 0.25/0.17/0.07 on CLINC150: a rule of thumb that works only with enough data.
6. **`strict_sequence` almost never deploys** (diagnostic: 0 errors in 37 accepted items already gives a 6.0% upper bound, so the walk stops at the first threshold; `evidence/diagnostics/strict_sequence_pitfall.csv`, Fig. 4). **`certify_once` deploys about 5-10% of the time**: the single selected threshold sits at the edge, so one-shot certification rarely confirms it. This models my reading of TRACER's changelog, not its implementation.
7. **`split_sequence` is near-nominal** (violation 4.5-7.2%) but loses coverage because 40% of the data picks the start.
8. When the target is looser than the student's overall error (e.g., CLINC150 at 0.05, Banking77 at 0.10) every gate accepts everything: sanity checks, not evidence.
9. "Violation (deployed)" in the raw tables is conditional on deploying; the guarantee is the unconditional rate.

## Limitations
Gold labels as teacher (no teacher noise); one frozen encoder and one student type; no temperature scaling; finite-population evaluation; i.i.d. draws (no drift/sessions); Bonferroni grid hand-chosen (32 points); min-max across 5 splits is a range, not a confidence interval; comparison to TRACER is by reading its code and changelog, not by running it; no analysis of why Wilson tracks the nominal level here (probably benign tail behaviour of these risk curves: untested).

## Next
Real LLM teacher (teacher noise, cost); drift streams with rolling recalibration and audit sampling; a stress test where Wilson should fail (small m with a flat risk curve, distribution shift); run TRACER's package on identical splits; more datasets and encoders; formal confidence intervals across splits.
