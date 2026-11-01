# ADR 0005: uniform audit sampling, rolling Holm recalibration, anytime-valid drift alarm

Status: accepted (2026-11-01). Evidence: `docs/notes/exp2-findings.md`.

## Context
A threshold certified once says nothing after the traffic shifts. We need (a) unbiased labelled
data from live traffic, (b) a way to re-certify, (c) an alarm that does not cry wolf when checked
continuously.

## Decision
1. A random fraction `audit_rate` of decisions is sent to the teacher regardless of confidence and
   stored. Escalated-but-unaudited items are NOT used for calibration: they are selected by low
   confidence, and mixing them with the uniform sample biases the risk estimate at thresholds
   below the current one. In shadow mode every item is audited, which is also uniform.
2. Recalibration re-runs the Holm gate on the last `window_labels` audited items every
   `recal_every` audits; if too few labels or nothing certifies, the gate withdraws and
   everything escalates (fail safe for accuracy, costly for spend).
3. The drift alarm uses the PrPl-EB confidence sequence (Waudby-Smith & Ramdas, arXiv 2010.09686)
   on the error of audited accepted items; alarm when its lower bound exceeds alpha. It is valid
   under continuous monitoring; we use the non-intersected bound because the mean may change.

## Consequences
- Each recalibration has its own failure probability delta; over many recalibrations the
  family-wise error is not controlled. Mitigation options (not implemented): spend delta over
  recalibrations (alpha-spending), or use anytime-valid risk certificates per threshold.
- Recovery speed is bounded by `labels / audit_rate` decisions; the audit rate is a cost knob.
- Importance-weighted audit sampling (more audits near the threshold) would be more label-efficient
  but needs weights in the estimator; left as future work.
