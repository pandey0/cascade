# exp2 findings: drift streams, audit sampling, rolling recalibration

Status: preliminary, single student seed per task. Teacher = gold labels (isolates drift from
teacher noise). 100 streams per cell, 3,000 pre-shift + 6,000 post-shift decisions, delta=0.1,
alpha 0.05 (Banking77) / 0.02 (CLINC150), recalibration every 250 decisions. Reproduce:
`scripts/exp2_prepare.py` -> `scripts/run_exp2.sh`. Tables: `results/exp2_*.md`.

Shifts (all built from real embeddings): **prior** (hardest 20% of classes get 5x weight),
**perturbed** (~15% of words corrupted, re-embedded), **unseen** (student trained without 15%
of classes; half of post traffic comes from them). Policies: `static_holm` (certify once),
`rolling_naive` (naive threshold on a sliding window of audited labels), `rolling_holm`
(Holm on the window). Only uniformly random audits feed the window (unbiased; see engine docs).

## Observations (audit 2% and 10%; "viol" = share of 500-decision post-shift blocks with
## accepted-risk above alpha)
1. **Mild shifts (prior, perturbed).** Static Holm drifts above target in 39-65% of Banking77
   blocks. Rolling Holm cut that to 2-33% (window 300: 2-8%, at lower coverage 0.41-0.61;
   window 1000: 12-33% at coverage 0.75-0.83). Rolling naive was worst: 51-91% of blocks violated.
2. **Cost of validity at small windows.** With 300 labels and alpha=0.02 (CLINC150), rolling
   Holm certifies almost nothing (coverage 0.00): you cannot certify a 2% risk from ~300 labels.
   Adaptivity and a tight target compete for the same audit budget.
3. **Severe shift (unseen classes).** No policy restores the target within 6,000 post decisions
   (risk 0.12-0.36 vs alpha 0.05/0.02). The window holds `labels / audit_rate` decisions
   (e.g. 1000 labels at 10% audit = 10,000 decisions), so it is mostly pre-shift data when the
   shift arrives. Rolling recalibration helps only when the window turns over faster than the
   shift matters; that needs more audit labels, which is the cost axis.
4. **Monitors.** The anytime-valid confidence-sequence alarm had 0 false alarms in the
   pre-shift phase in every cell. The windowed z-test, re-evaluated at each audited item, raised
   false alarms in 0-22% of streams (highest at 10% audit). The price of validity is delay: on
   the unseen shift (10% audit) the median delay was ~3,400 decisions vs ~100-430 for the z-test,
   and the CS often did not fire at all at 2% audit (detect rate 0.00-0.23).

## Caveats
- One student per task, one shift instance each; shifts are synthetic constructions on real data.
- Per-recalibration guarantee only: repeated recalibration is not family-wise controlled (ADR 0005).
- The monitor assumes a constant mean; used here as a change alarm, not a post-shift certificate.
- Block-level violation includes blocks with very few accepted items (noisy estimates).
