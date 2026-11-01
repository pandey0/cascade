Target risk alpha=0.02, confidence delta=0.1. Real pools: 3 split(s), means across splits.

| method | m | deploy rate | violation rate (all trials) | violation (deployed) | mean coverage | mean true risk (deployed) |
|---|---|---|---|---|---|---|
| naive | 250 | 1.000 | 0.430 | 0.430 | 0.962 | 0.0200 |
| certify_once | 250 | 0.000 | 0.000 | nan | 0.000 | nan |
| strict_sequence | 250 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 250 | 0.000 | 0.000 | nan | 0.000 | nan |
| split_sequence | 250 | 0.234 | 0.036 | 0.151 | 0.217 | 0.0129 |
| naive | 500 | 1.000 | 0.492 | 0.492 | 0.966 | 0.0204 |
| certify_once | 500 | 0.000 | 0.000 | nan | 0.000 | nan |
| strict_sequence | 500 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 500 | 0.762 | 0.001 | 0.001 | 0.627 | 0.0048 |
| split_sequence | 500 | 0.482 | 0.067 | 0.138 | 0.449 | 0.0135 |
| naive | 1000 | 1.000 | 0.538 | 0.538 | 0.968 | 0.0204 |
| certify_once | 1000 | 0.046 | 0.012 | 0.253 | 0.044 | 0.0175 |
| strict_sequence | 1000 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 1000 | 1.000 | 0.002 | 0.002 | 0.899 | 0.0081 |
| split_sequence | 1000 | 0.623 | 0.052 | 0.083 | 0.586 | 0.0139 |
| naive | 2000 | 1.000 | 0.443 | 0.443 | 0.967 | 0.0199 |
| certify_once | 2000 | 0.073 | 0.008 | 0.117 | 0.070 | 0.0168 |
| strict_sequence | 2000 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 2000 | 1.000 | 0.002 | 0.002 | 0.926 | 0.0108 |
| split_sequence | 2000 | 0.804 | 0.048 | 0.060 | 0.762 | 0.0150 |
