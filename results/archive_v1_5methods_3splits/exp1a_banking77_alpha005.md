Target risk alpha=0.05, confidence delta=0.1. Real pools: 3 split(s), means across splits.

| method | m | deploy rate | violation rate (all trials) | violation (deployed) | mean coverage | mean true risk (deployed) |
|---|---|---|---|---|---|---|
| naive | 250 | 1.000 | 0.539 | 0.539 | 0.941 | 0.0524 |
| certify_once | 250 | 0.077 | 0.036 | 0.471 | 0.072 | 0.0488 |
| strict_sequence | 250 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 250 | 0.796 | 0.004 | 0.005 | 0.586 | 0.0151 |
| split_sequence | 250 | 0.388 | 0.060 | 0.154 | 0.341 | 0.0354 |
| naive | 500 | 1.000 | 0.535 | 0.535 | 0.940 | 0.0509 |
| certify_once | 500 | 0.077 | 0.020 | 0.254 | 0.071 | 0.0426 |
| strict_sequence | 500 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 500 | 0.999 | 0.001 | 0.001 | 0.816 | 0.0222 |
| split_sequence | 500 | 0.628 | 0.059 | 0.094 | 0.561 | 0.0366 |
| naive | 1000 | 1.000 | 0.498 | 0.498 | 0.939 | 0.0501 |
| certify_once | 1000 | 0.111 | 0.023 | 0.212 | 0.103 | 0.0452 |
| strict_sequence | 1000 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 1000 | 1.000 | 0.001 | 0.001 | 0.865 | 0.0295 |
| split_sequence | 1000 | 0.828 | 0.072 | 0.087 | 0.748 | 0.0388 |
| naive | 2000 | 1.000 | 0.487 | 0.487 | 0.939 | 0.0497 |
| certify_once | 2000 | 0.098 | 0.019 | 0.189 | 0.091 | 0.0458 |
| strict_sequence | 2000 | 0.034 | 0.001 | 0.022 | 0.032 | 0.0433 |
| bonferroni | 2000 | 1.000 | 0.000 | 0.000 | 0.891 | 0.0350 |
| split_sequence | 2000 | 0.967 | 0.055 | 0.057 | 0.885 | 0.0413 |
