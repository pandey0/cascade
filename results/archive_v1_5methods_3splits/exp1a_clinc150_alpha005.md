Target risk alpha=0.05, confidence delta=0.1. Real pools: 3 split(s), means across splits.

| method | m | deploy rate | violation rate (all trials) | violation (deployed) | mean coverage | mean true risk (deployed) |
|---|---|---|---|---|---|---|
| naive | 250 | 1.000 | 0.000 | 0.000 | 0.999 | 0.0329 |
| certify_once | 250 | 0.193 | 0.000 | 0.000 | 0.192 | 0.0321 |
| strict_sequence | 250 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 250 | 0.997 | 0.000 | 0.000 | 0.934 | 0.0151 |
| split_sequence | 250 | 0.510 | 0.000 | 0.000 | 0.505 | 0.0287 |
| naive | 500 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0332 |
| certify_once | 500 | 0.159 | 0.000 | 0.000 | 0.159 | 0.0331 |
| strict_sequence | 500 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 500 | 1.000 | 0.000 | 0.000 | 0.976 | 0.0233 |
| split_sequence | 500 | 0.735 | 0.000 | 0.000 | 0.732 | 0.0310 |
| naive | 1000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0332 |
| certify_once | 1000 | 0.331 | 0.000 | 0.000 | 0.331 | 0.0332 |
| strict_sequence | 1000 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 1000 | 1.000 | 0.000 | 0.000 | 0.990 | 0.0280 |
| split_sequence | 1000 | 0.908 | 0.000 | 0.000 | 0.907 | 0.0325 |
| naive | 2000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0332 |
| certify_once | 2000 | 0.647 | 0.000 | 0.000 | 0.647 | 0.0332 |
| strict_sequence | 2000 | 0.349 | 0.000 | 0.000 | 0.349 | 0.0332 |
| bonferroni | 2000 | 1.000 | 0.000 | 0.000 | 0.993 | 0.0290 |
| split_sequence | 2000 | 0.988 | 0.000 | 0.000 | 0.988 | 0.0332 |
