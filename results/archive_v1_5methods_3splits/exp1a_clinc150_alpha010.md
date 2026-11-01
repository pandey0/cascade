Target risk alpha=0.1, confidence delta=0.1. Real pools: 3 split(s), means across splits.

| method | m | deploy rate | violation rate (all trials) | violation (deployed) | mean coverage | mean true risk (deployed) |
|---|---|---|---|---|---|---|
| naive | 250 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0332 |
| certify_once | 250 | 0.512 | 0.000 | 0.000 | 0.512 | 0.0332 |
| strict_sequence | 250 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 250 | 1.000 | 0.000 | 0.000 | 0.993 | 0.0289 |
| split_sequence | 250 | 0.976 | 0.000 | 0.000 | 0.976 | 0.0332 |
| naive | 500 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0332 |
| certify_once | 500 | 0.881 | 0.000 | 0.000 | 0.881 | 0.0332 |
| strict_sequence | 500 | 0.003 | 0.000 | 0.000 | 0.003 | 0.0325 |
| bonferroni | 500 | 1.000 | 0.000 | 0.000 | 0.993 | 0.0291 |
| split_sequence | 500 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0332 |
| naive | 1000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0332 |
| certify_once | 1000 | 0.998 | 0.000 | 0.000 | 0.998 | 0.0332 |
| strict_sequence | 1000 | 0.442 | 0.000 | 0.000 | 0.442 | 0.0332 |
| bonferroni | 1000 | 1.000 | 0.000 | 0.000 | 0.993 | 0.0291 |
| split_sequence | 1000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0332 |
| naive | 2000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0332 |
| certify_once | 2000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0332 |
| strict_sequence | 2000 | 0.999 | 0.000 | 0.000 | 0.999 | 0.0332 |
| bonferroni | 2000 | 1.000 | 0.000 | 0.000 | 0.993 | 0.0291 |
| split_sequence | 2000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0332 |
