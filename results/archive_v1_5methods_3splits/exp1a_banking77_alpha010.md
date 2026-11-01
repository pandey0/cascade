Target risk alpha=0.1, confidence delta=0.1. Real pools: 3 split(s), means across splits.

| method | m | deploy rate | violation rate (all trials) | violation (deployed) | mean coverage | mean true risk (deployed) |
|---|---|---|---|---|---|---|
| naive | 250 | 1.000 | 0.000 | 0.000 | 0.999 | 0.0799 |
| certify_once | 250 | 0.085 | 0.000 | 0.000 | 0.085 | 0.0777 |
| strict_sequence | 250 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 250 | 1.000 | 0.000 | 0.000 | 0.932 | 0.0494 |
| split_sequence | 250 | 0.709 | 0.000 | 0.000 | 0.694 | 0.0693 |
| naive | 500 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0805 |
| certify_once | 500 | 0.179 | 0.000 | 0.000 | 0.179 | 0.0801 |
| strict_sequence | 500 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 500 | 1.000 | 0.000 | 0.000 | 0.966 | 0.0622 |
| split_sequence | 500 | 0.878 | 0.000 | 0.000 | 0.868 | 0.0740 |
| naive | 1000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0807 |
| certify_once | 1000 | 0.366 | 0.000 | 0.000 | 0.366 | 0.0806 |
| strict_sequence | 1000 | 0.164 | 0.000 | 0.000 | 0.164 | 0.0800 |
| bonferroni | 1000 | 1.000 | 0.000 | 0.000 | 0.984 | 0.0715 |
| split_sequence | 1000 | 0.981 | 0.000 | 0.000 | 0.976 | 0.0777 |
| naive | 2000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0807 |
| certify_once | 2000 | 0.429 | 0.000 | 0.000 | 0.429 | 0.0807 |
| strict_sequence | 2000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.0807 |
| bonferroni | 2000 | 1.000 | 0.000 | 0.000 | 0.993 | 0.0763 |
| split_sequence | 2000 | 0.998 | 0.000 | 0.000 | 0.996 | 0.0801 |
