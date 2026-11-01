Target risk alpha=0.1, confidence delta=0.1. Synthetic scores (see sim.py).

| method | m | deploy rate | violation rate (all trials) | violation (deployed) | mean coverage | mean true risk (deployed) |
|---|---|---|---|---|---|---|
| naive | 200 | 1.000 | 0.492 | 0.492 | 0.936 | 0.0945 |
| certify_once | 200 | 0.066 | 0.028 | 0.424 | 0.058 | 0.0881 |
| strict_sequence | 200 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 200 | 0.278 | 0.004 | 0.014 | 0.163 | 0.0529 |
| split_sequence | 200 | 0.264 | 0.054 | 0.205 | 0.216 | 0.0787 |
| naive | 500 | 1.000 | 0.546 | 0.546 | 0.960 | 0.0976 |
| certify_once | 500 | 0.094 | 0.018 | 0.191 | 0.084 | 0.0879 |
| strict_sequence | 500 | 0.000 | 0.000 | nan | 0.000 | nan |
| bonferroni | 500 | 0.910 | 0.004 | 0.004 | 0.544 | 0.0539 |
| split_sequence | 500 | 0.742 | 0.066 | 0.089 | 0.599 | 0.0769 |
| naive | 1000 | 1.000 | 0.526 | 0.526 | 0.967 | 0.0985 |
| certify_once | 1000 | 0.120 | 0.042 | 0.350 | 0.112 | 0.0931 |
| strict_sequence | 1000 | 0.258 | 0.018 | 0.070 | 0.227 | 0.0855 |
| bonferroni | 1000 | 1.000 | 0.000 | 0.000 | 0.740 | 0.0681 |
| split_sequence | 1000 | 0.942 | 0.084 | 0.089 | 0.807 | 0.0823 |
| naive | 3000 | 1.000 | 0.512 | 0.512 | 0.974 | 0.0995 |
| certify_once | 3000 | 0.126 | 0.030 | 0.238 | 0.120 | 0.0955 |
| strict_sequence | 3000 | 1.000 | 0.094 | 0.094 | 0.933 | 0.0924 |
| bonferroni | 3000 | 1.000 | 0.000 | 0.000 | 0.861 | 0.0821 |
| split_sequence | 3000 | 1.000 | 0.090 | 0.090 | 0.917 | 0.0901 |
