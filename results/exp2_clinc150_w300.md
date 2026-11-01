alpha=0.02, delta=0.1, 100 streams per cell, 3000 pre + 6000 post decisions, window 300 labels.

| pool | policy | audit | post risk | post cov | block viol | recovery (decisions) | false alarm CS / z | detect CS / z | delay CS / z |
|---|---|---|---|---|---|---|---|---|---|
| drift_clinc150_prior | static_holm | 0.02 | 0.022 | 0.90 | 0.58 | 1000 | 0.00 / 0.00 | 0.00 / 0.03 | nan / 1224 |
| drift_clinc150_prior | static_holm | 0.05 | 0.022 | 0.90 | 0.58 | 1000 | 0.00 / 0.00 | 0.00 / 0.10 | nan / 3202 |
| drift_clinc150_prior | static_holm | 0.10 | 0.022 | 0.90 | 0.58 | 1000 | 0.00 / 0.01 | 0.00 / 0.22 | nan / 2584 |
| drift_clinc150_prior | rolling_naive | 0.02 | 0.030 | 0.93 | 0.76 | 2500 | 0.00 / 0.00 | 0.00 / 0.10 | nan / 2084 |
| drift_clinc150_prior | rolling_naive | 0.05 | 0.027 | 0.91 | 0.67 | 2000 | 0.00 / 0.03 | 0.00 / 0.28 | nan / 3878 |
| drift_clinc150_prior | rolling_naive | 0.10 | 0.024 | 0.90 | 0.59 | 2000 | 0.00 / 0.10 | 0.00 / 0.47 | nan / 2213 |
| drift_clinc150_prior | rolling_holm | 0.02 | 0.032 | 0.00 | 0.67 | 500 | 0.00 / 0.00 | 0.00 / 0.00 | nan / nan |
| drift_clinc150_prior | rolling_holm | 0.05 | 0.032 | 0.00 | 0.80 | 500 | 0.00 / 0.00 | 0.00 / 0.00 | nan / nan |
| drift_clinc150_prior | rolling_holm | 0.10 | 0.026 | 0.00 | 1.00 | 500 | 0.00 / 0.00 | 0.00 / 0.00 | nan / nan |
| drift_clinc150_perturbed | static_holm | 0.02 | 0.018 | 0.81 | 0.37 | 500 | 0.00 / 0.00 | 0.00 / 0.00 | nan / nan |
| drift_clinc150_perturbed | static_holm | 0.05 | 0.018 | 0.81 | 0.37 | 500 | 0.00 / 0.00 | 0.00 / 0.08 | nan / 4245 |
| drift_clinc150_perturbed | static_holm | 0.10 | 0.018 | 0.81 | 0.37 | 500 | 0.00 / 0.01 | 0.00 / 0.17 | nan / 2619 |
| drift_clinc150_perturbed | rolling_naive | 0.02 | 0.029 | 0.85 | 0.69 | 2500 | 0.00 / 0.00 | 0.00 / 0.11 | nan / 2482 |
| drift_clinc150_perturbed | rolling_naive | 0.05 | 0.026 | 0.84 | 0.61 | 2000 | 0.00 / 0.03 | 0.00 / 0.22 | nan / 2610 |
| drift_clinc150_perturbed | rolling_naive | 0.10 | 0.024 | 0.83 | 0.57 | 2000 | 0.00 / 0.10 | 0.00 / 0.32 | nan / 1856 |
| drift_clinc150_perturbed | rolling_holm | 0.02 | nan | 0.00 | nan | 500 | 0.00 / 0.00 | 0.00 / 0.00 | nan / nan |
| drift_clinc150_perturbed | rolling_holm | 0.05 | 0.019 | 0.00 | 0.00 | 500 | 0.00 / 0.00 | 0.00 / 0.00 | nan / nan |
| drift_clinc150_perturbed | rolling_holm | 0.10 | 0.027 | 0.00 | 0.50 | 500 | 0.00 / 0.00 | 0.00 / 0.00 | nan / nan |
| drift_clinc150_unseen | static_holm | 0.02 | 0.293 | 0.67 | 1.00 | inf | 0.00 / 0.01 | 0.13 / 0.99 | 5051 / 1314 |
| drift_clinc150_unseen | static_holm | 0.05 | 0.293 | 0.67 | 1.00 | inf | 0.00 / 0.00 | 0.76 / 1.00 | 4427 / 611 |
| drift_clinc150_unseen | static_holm | 0.10 | 0.293 | 0.67 | 1.00 | inf | 0.00 / 0.01 | 0.99 / 0.99 | 3349 / 303 |
| drift_clinc150_unseen | rolling_naive | 0.02 | 0.177 | 0.52 | 1.00 | inf | 0.00 / 0.03 | 0.00 / 0.96 | nan / 640 |
| drift_clinc150_unseen | rolling_naive | 0.05 | 0.129 | 0.31 | 0.98 | 5000 | 0.00 / 0.02 | 0.00 / 0.98 | nan / 382 |
| drift_clinc150_unseen | rolling_naive | 0.10 | 0.116 | 0.19 | 0.96 | 3000 | 0.00 / 0.05 | 0.00 / 0.95 | nan / 140 |
| drift_clinc150_unseen | rolling_holm | 0.02 | 0.280 | 0.00 | 1.00 | 500 | 0.00 / 0.00 | 0.00 / 0.00 | nan / nan |
| drift_clinc150_unseen | rolling_holm | 0.05 | 0.282 | 0.00 | 1.00 | 500 | 0.00 / 0.00 | 0.00 / 0.01 | nan / 230 |
| drift_clinc150_unseen | rolling_holm | 0.10 | 0.268 | 0.00 | 1.00 | 500 | 0.00 / 0.00 | 0.00 / 0.01 | nan / 138 |
