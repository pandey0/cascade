alpha=0.02, delta=0.1, 100 streams per cell, 3000 pre + 6000 post decisions, window 1000 labels.

| pool | policy | audit | post risk | post cov | block viol | recovery (decisions) | false alarm CS / z | detect CS / z | delay CS / z |
|---|---|---|---|---|---|---|---|---|---|
| drift_clinc150_prior | static_holm | 0.02 | 0.022 | 0.90 | 0.58 | 1000 | 0.00 / 0.00 | 0.00 / 0.03 | nan / 1224 |
| drift_clinc150_prior | static_holm | 0.05 | 0.022 | 0.90 | 0.58 | 1000 | 0.00 / 0.00 | 0.00 / 0.10 | nan / 3202 |
| drift_clinc150_prior | static_holm | 0.10 | 0.022 | 0.90 | 0.58 | 1000 | 0.00 / 0.01 | 0.00 / 0.22 | nan / 2584 |
| drift_clinc150_prior | rolling_naive | 0.02 | 0.035 | 0.94 | 0.90 | inf | 0.00 / 0.01 | 0.00 / 0.13 | nan / 3494 |
| drift_clinc150_prior | rolling_naive | 0.05 | 0.032 | 0.94 | 0.84 | 4000 | 0.00 / 0.04 | 0.00 / 0.43 | nan / 3370 |
| drift_clinc150_prior | rolling_naive | 0.10 | 0.029 | 0.93 | 0.78 | 3500 | 0.00 / 0.08 | 0.00 / 0.61 | nan / 2191 |
| drift_clinc150_prior | rolling_holm | 0.02 | 0.016 | 0.86 | 0.28 | 500 | 0.00 / 0.00 | 0.00 / 0.00 | nan / nan |
| drift_clinc150_prior | rolling_holm | 0.05 | 0.014 | 0.84 | 0.23 | 500 | 0.00 / 0.00 | 0.00 / 0.03 | nan / 4905 |
| drift_clinc150_prior | rolling_holm | 0.10 | 0.013 | 0.81 | 0.18 | 500 | 0.00 / 0.00 | 0.00 / 0.04 | nan / 2960 |
| drift_clinc150_perturbed | static_holm | 0.02 | 0.018 | 0.81 | 0.37 | 500 | 0.00 / 0.00 | 0.00 / 0.00 | nan / nan |
| drift_clinc150_perturbed | static_holm | 0.05 | 0.018 | 0.81 | 0.37 | 500 | 0.00 / 0.00 | 0.00 / 0.08 | nan / 4245 |
| drift_clinc150_perturbed | static_holm | 0.10 | 0.018 | 0.81 | 0.37 | 500 | 0.00 / 0.01 | 0.00 / 0.17 | nan / 2619 |
| drift_clinc150_perturbed | rolling_naive | 0.02 | 0.032 | 0.87 | 0.82 | 4000 | 0.00 / 0.01 | 0.00 / 0.11 | nan / 4029 |
| drift_clinc150_perturbed | rolling_naive | 0.05 | 0.030 | 0.86 | 0.77 | 3000 | 0.00 / 0.04 | 0.00 / 0.27 | nan / 2629 |
| drift_clinc150_perturbed | rolling_naive | 0.10 | 0.027 | 0.85 | 0.70 | 2500 | 0.00 / 0.08 | 0.00 / 0.48 | nan / 2038 |
| drift_clinc150_perturbed | rolling_holm | 0.02 | 0.013 | 0.76 | 0.16 | 500 | 0.00 / 0.00 | 0.00 / 0.00 | nan / nan |
| drift_clinc150_perturbed | rolling_holm | 0.05 | 0.012 | 0.75 | 0.14 | 500 | 0.00 / 0.00 | 0.00 / 0.02 | nan / 4184 |
| drift_clinc150_perturbed | rolling_holm | 0.10 | 0.011 | 0.72 | 0.11 | 500 | 0.00 / 0.00 | 0.00 / 0.01 | nan / 3913 |
| drift_clinc150_unseen | static_holm | 0.02 | 0.293 | 0.67 | 1.00 | inf | 0.00 / 0.01 | 0.13 / 0.99 | 5051 / 1314 |
| drift_clinc150_unseen | static_holm | 0.05 | 0.293 | 0.67 | 1.00 | inf | 0.00 / 0.00 | 0.76 / 1.00 | 4427 / 611 |
| drift_clinc150_unseen | static_holm | 0.10 | 0.293 | 0.67 | 1.00 | inf | 0.00 / 0.01 | 0.99 / 0.99 | 3349 / 303 |
| drift_clinc150_unseen | rolling_naive | 0.02 | 0.275 | 0.66 | 1.00 | inf | 0.00 / 0.02 | 0.06 / 0.98 | 4740 / 538 |
| drift_clinc150_unseen | rolling_naive | 0.05 | 0.195 | 0.56 | 1.00 | inf | 0.00 / 0.03 | 0.13 / 0.97 | 4887 / 319 |
| drift_clinc150_unseen | rolling_naive | 0.10 | 0.143 | 0.42 | 1.00 | inf | 0.00 / 0.11 | 0.06 / 0.89 | 3456 / 119 |
| drift_clinc150_unseen | rolling_holm | 0.02 | 0.159 | 0.49 | 1.00 | inf | 0.00 / 0.00 | 0.00 / 0.91 | nan / 1795 |
| drift_clinc150_unseen | rolling_holm | 0.05 | 0.132 | 0.28 | 1.00 | 4000 | 0.00 / 0.00 | 0.00 / 0.93 | nan / 1101 |
| drift_clinc150_unseen | rolling_holm | 0.10 | 0.131 | 0.15 | 1.00 | 2500 | 0.00 / 0.00 | 0.00 / 0.88 | nan / 404 |
