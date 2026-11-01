# Journal
## 2026-11-01
Scaffolded the package (bounds, gates, metrics, students, spec, teacher cache, splitter, gateway skeleton, CLI). Read the TRACER paper and repo; wrote the analysis and extension plan. Ran experiment 0 on synthetic scores: naive gates miss the target about half the time; certified selection holds delta but needs thousands of audited examples. Next: Docker build check, git init, read `tracer/fit/*`, reproduce a Banking77 baseline.

## 2026-11-01 (later)
Ran experiment 1a on real data (Banking77, CLINC150; MiniLM + logistic regression; gold labels as teacher). Found my strict-start fixed-sequence gate had a power flaw and that my earlier "needs thousands of audit examples" claim was partly an artifact; added Bonferroni and split-sequence gates, re-ran everything, corrected docs (ADR 0004, exp1a-findings). Naive selection misses its target in about half of draws (small margins); validity costs about 4-13 coverage points at 1,000-2,000 audit labels on the real tasks. Next: Holm step-down + margin baseline, across-split intervals, real LLM teacher.

## 2026-11-01 (evidence run)
Full pipeline (`scripts/run_all.sh`): 5 splits per task, 8 gates, manifests + ledger + logs, 4 generated figures, LaTeX table, draft paper scaffold. Findings: naive ~45-54% violation; Holm ~= Bonferroni (+<=1 pt); uncorrected Wilson margin is near-nominal on these benign tasks (no guarantee) - this tempers the "validity is expensive" message. Fixed plot issues found by viewing the figures (clipped label, overlapping lines, wrong axis note).

## 2026-11-01 exp1b
Labelled 2000/task with Claude Haiku 5.5 (Banking77 76.5%, CLINC150 90.9% vs gold, $0.89). Gates run on teacher-disagreement and gold-error targets; see docs/notes/exp1b-findings.md.

## 2026-11-01 completion pass
Added drift module + exp2, economics model, decision engine, hardened gateway, audit store, artifact format, micro-batching, ops (alerts, dashboard), docs (architecture, runbook, SLO, security, perf), Terraform/Helm (unapplied), CI extensions, paper sections for teacher noise and drift. Honest gaps in `SCORECARD.md` and `COMPLETION-PLAN.md`. Dead end recorded: pinning torch to 1 thread made throughput worse.
