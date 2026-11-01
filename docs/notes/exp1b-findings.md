# exp1b findings: gates with a noisy LLM teacher (Claude Haiku 5.5)

Status: preliminary. 3 splits x 1000-item pools per task, calibration sizes 100/200/400, 400 trials,
delta=0.1, alpha 0.05 and 0.10. One teacher, one prompt (v1), one encoder (MiniLM). Reproduce:
`scripts/label_with_teacher.py` -> `scripts/exp1b_prepare.py` -> `scripts/run_exp1b.sh` (about 100 min CPU).
Teacher accuracy vs gold: Banking77 76.5% (n=2000), CLINC150 90.9% (n=2000). Spend about $0.89.

Numbers below are at m=400 ("violation" = true risk of the chosen threshold exceeds alpha,
over all draws; non-deployments count as no violation).

## Observations
1. Risk measured as disagreement with the teacher: Bonferroni and Holm violated in <=0.1% of
   draws everywhere; naive violated in 30-55%, safety-factor 2-23%, Wilson 2-5%.
   The earlier exp1a ranking carries over to a real noisy teacher.
2. Distilled students (trained on teacher labels): the guarantee is about agreement with the
   teacher, not truth. Banking77 alpha=0.10: Bonferroni deploys in 100% of draws and its gold
   risk exceeds alpha in 70% of them (mean gold risk of the deployed gate 0.105). CLINC150
   (teacher 91% correct) is mostly fine (<1%).
3. Gold-trained students (92%/97% accurate vs gold, more accurate than the teacher): the gold
   risk is ~0.006 (Banking77) and 0.000-0.003 (CLINC150), far below alpha, but the gate certifies
   little because agreement with a worse teacher caps coverage. Banking77 alpha=0.05: Bonferroni
   and Holm deploy 0%. Agreement with the teacher is both not sufficient (obs. 2) and not necessary
   (obs. 3) for correctness.

## Caveats
- Teacher noise here is one model's behaviour on a 77-way task; not a general claim.
- Gold labels in these benchmarks have their own errors.
- Pools are 1000 items; coverage/risk of each threshold is exact for the pool, not the population.
- m=400 only; smaller m rows are in results/exp1b_*.json.
