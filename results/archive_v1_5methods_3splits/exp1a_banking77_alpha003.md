Target risk alpha=0.03, confidence delta=0.1. Real pools: 3 split(s), means across splits.

| method | m | deploy rate | violation rate (all trials) | violation (deployed) | mean coverage | mean true risk (deployed) |
|---|---|---|---|---|---|---|
| naive | 250 | 1.000 | 0.552 | 0.552 | 0.872 | 0.0325 |
| certify_once | 250 | 0.000 | 0.000 | nan | 0.000 | nan |
| strict_sequence | 250 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 250 | 0.063 | 0.001 | 0.013 | 0.050 | 0.0168 |
| split_sequence | 250 | 0.158 | 0.039 | 0.245 | 0.128 | 0.0228 |
| naive | 500 | 1.000 | 0.542 | 0.542 | 0.870 | 0.0311 |
| certify_once | 500 | 0.089 | 0.027 | 0.303 | 0.076 | 0.0261 |
| strict_sequence | 500 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 500 | 0.714 | 0.001 | 0.001 | 0.476 | 0.0096 |
| split_sequence | 500 | 0.406 | 0.043 | 0.105 | 0.327 | 0.0206 |
| naive | 1000 | 1.000 | 0.499 | 0.499 | 0.868 | 0.0301 |
| certify_once | 1000 | 0.077 | 0.020 | 0.262 | 0.066 | 0.0263 |
| strict_sequence | 1000 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 1000 | 0.996 | 0.000 | 0.000 | 0.740 | 0.0135 |
| split_sequence | 1000 | 0.654 | 0.057 | 0.088 | 0.536 | 0.0217 |
| naive | 2000 | 1.000 | 0.487 | 0.487 | 0.869 | 0.0300 |
| certify_once | 2000 | 0.081 | 0.012 | 0.152 | 0.069 | 0.0265 |
| strict_sequence | 2000 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 2000 | 1.000 | 0.000 | 0.000 | 0.797 | 0.0177 |
| split_sequence | 2000 | 0.865 | 0.048 | 0.056 | 0.720 | 0.0233 |
