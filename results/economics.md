Break-even decisions V* = (labels*c_T + fixed) / (coverage*(c_T*(1-audit) - c_S)).
c_T measured from the Claude Haiku 5.5 labelling run; c_S = 0 (CPU logistic regression,
not costed); fixed cost = 0 (engineering time excluded).
Coverage values are illustrative operating points.

| task | c_T (USD/call) | coverage | audit rate | labels | V* (decisions) |
|---|---|---|---|---|---|
| banking77 | 0.000204 | 0.3 | 0.00 | 3000 | 10,000 |
| banking77 | 0.000204 | 0.3 | 0.05 | 3000 | 10,526 |
| banking77 | 0.000204 | 0.3 | 0.20 | 3000 | 12,500 |
| banking77 | 0.000204 | 0.6 | 0.00 | 3000 | 5,000 |
| banking77 | 0.000204 | 0.6 | 0.05 | 3000 | 5,263 |
| banking77 | 0.000204 | 0.6 | 0.20 | 3000 | 6,250 |
| banking77 | 0.000204 | 0.9 | 0.00 | 3000 | 3,333 |
| banking77 | 0.000204 | 0.9 | 0.05 | 3000 | 3,509 |
| banking77 | 0.000204 | 0.9 | 0.20 | 3000 | 4,167 |
| clinc150 | 0.000243 | 0.3 | 0.00 | 3000 | 10,000 |
| clinc150 | 0.000243 | 0.3 | 0.05 | 3000 | 10,526 |
| clinc150 | 0.000243 | 0.3 | 0.20 | 3000 | 12,500 |
| clinc150 | 0.000243 | 0.6 | 0.00 | 3000 | 5,000 |
| clinc150 | 0.000243 | 0.6 | 0.05 | 3000 | 5,263 |
| clinc150 | 0.000243 | 0.6 | 0.20 | 3000 | 6,250 |
| clinc150 | 0.000243 | 0.9 | 0.00 | 3000 | 3,333 |
| clinc150 | 0.000243 | 0.9 | 0.05 | 3000 | 3,509 |
| clinc150 | 0.000243 | 0.9 | 0.20 | 3000 | 4,167 |

## With hosting and engineering time (the numbers that decide whether it is worth it)
Assumptions, NOT measurements unless stated: LLM cost per call = measured Banking77
value (no prompt caching) or an illustrative 10x cheaper value with prompt caching;
the small model serves ~50 requests/s per node (measured 30-70 on 4 pinned cores) on
a node assumed to cost $0.15/hour; 2 replicas always on ($7.2/day); 50% of requests
answered cheaply; 5% audited; $10,000 of engineering time to adopt.

| LLM cost/call | break-even volume (covers hosting) | payback of $10k at 100k/day | at 1M/day | at 10M/day |
|---|---|---|---|---|
| $0.000204 (measured, no caching) | 74,602 requests/day | 4,080 days | 112 days | 10 days |
| $0.000020 (illustrative, with caching) | 776,177 requests/day | never | 4,816 days | 117 days |
