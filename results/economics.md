Break-even decisions V* = (labels*c_T + fixed) / (coverage*(c_T*(1-audit) - c_S)).
c_T measured from the Claude Haiku 5.5 labelling run; c_S = 0 (CPU logistic regression,
not costed); fixed cost = 0 (engineering time excluded). Coverage values are illustrative.

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
