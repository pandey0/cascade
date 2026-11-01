alpha=0.05, delta=0.1, 100 streams per cell, 3000 pre + 6000 post decisions, window 300 labels.

| pool | policy | audit | post risk | post cov | block viol | recovery (decisions) | false alarm CS / z | detect CS / z | delay CS / z |
|---|---|---|---|---|---|---|---|---|---|
| drift_banking77_prior | static_holm | 0.02 | 0.055 | 0.87 | 0.65 | 1000 | 0.00 / 0.01 | 0.00 / 0.03 | nan / 484 |
| drift_banking77_prior | static_holm | 0.05 | 0.055 | 0.87 | 0.65 | 1000 | 0.00 / 0.02 | 0.00 / 0.16 | nan / 4013 |
| drift_banking77_prior | static_holm | 0.10 | 0.055 | 0.87 | 0.65 | 1000 | 0.00 / 0.02 | 0.00 / 0.34 | nan / 3049 |
| drift_banking77_prior | rolling_naive | 0.02 | 0.070 | 0.90 | 0.82 | 5500 | 0.00 / 0.02 | 0.00 / 0.13 | nan / 3942 |
| drift_banking77_prior | rolling_naive | 0.05 | 0.059 | 0.88 | 0.64 | 3000 | 0.00 / 0.06 | 0.00 / 0.37 | nan / 2819 |
| drift_banking77_prior | rolling_naive | 0.10 | 0.054 | 0.86 | 0.55 | 2000 | 0.00 / 0.09 | 0.00 / 0.48 | nan / 1398 |
| drift_banking77_prior | rolling_holm | 0.02 | 0.028 | 0.61 | 0.08 | 500 | 0.00 / 0.01 | 0.00 / 0.00 | nan / nan |
| drift_banking77_prior | rolling_holm | 0.05 | 0.023 | 0.52 | 0.04 | 500 | 0.00 / 0.00 | 0.00 / 0.00 | nan / nan |
| drift_banking77_prior | rolling_holm | 0.10 | 0.021 | 0.42 | 0.02 | 500 | 0.00 / 0.01 | 0.00 / 0.00 | nan / nan |
| drift_banking77_perturbed | static_holm | 0.02 | 0.047 | 0.79 | 0.39 | 500 | 0.00 / 0.01 | 0.00 / 0.06 | nan / 3348 |
| drift_banking77_perturbed | static_holm | 0.05 | 0.047 | 0.79 | 0.39 | 500 | 0.00 / 0.02 | 0.00 / 0.11 | nan / 3807 |
| drift_banking77_perturbed | static_holm | 0.10 | 0.047 | 0.79 | 0.39 | 500 | 0.00 / 0.02 | 0.00 / 0.09 | nan / 2936 |
| drift_banking77_perturbed | rolling_naive | 0.02 | 0.064 | 0.84 | 0.72 | 3000 | 0.00 / 0.02 | 0.00 / 0.21 | nan / 2931 |
| drift_banking77_perturbed | rolling_naive | 0.05 | 0.056 | 0.82 | 0.58 | 2000 | 0.00 / 0.06 | 0.00 / 0.31 | nan / 2957 |
| drift_banking77_perturbed | rolling_naive | 0.10 | 0.054 | 0.81 | 0.51 | 1500 | 0.00 / 0.09 | 0.00 / 0.35 | nan / 1222 |
| drift_banking77_perturbed | rolling_holm | 0.02 | 0.021 | 0.54 | 0.04 | 500 | 0.00 / 0.01 | 0.00 / 0.00 | nan / nan |
| drift_banking77_perturbed | rolling_holm | 0.05 | 0.018 | 0.46 | 0.01 | 500 | 0.00 / 0.00 | 0.00 / 0.00 | nan / nan |
| drift_banking77_perturbed | rolling_holm | 0.10 | 0.018 | 0.41 | 0.03 | 500 | 0.00 / 0.01 | 0.00 / 0.00 | nan / nan |
| drift_banking77_unseen | static_holm | 0.02 | 0.359 | 0.70 | 1.00 | inf | 0.00 / 0.02 | 0.23 / 0.97 | 4539 / 1413 |
| drift_banking77_unseen | static_holm | 0.05 | 0.359 | 0.70 | 1.00 | inf | 0.00 / 0.01 | 0.76 / 0.99 | 4099 / 753 |
| drift_banking77_unseen | static_holm | 0.10 | 0.359 | 0.70 | 1.00 | inf | 0.00 / 0.05 | 0.97 / 0.95 | 3457 / 432 |
| drift_banking77_unseen | rolling_naive | 0.02 | 0.269 | 0.57 | 0.99 | inf | 0.00 / 0.02 | 0.01 / 0.98 | 5935 / 858 |
| drift_banking77_unseen | rolling_naive | 0.05 | 0.166 | 0.36 | 0.84 | 5000 | 0.00 / 0.07 | 0.00 / 0.93 | nan / 432 |
| drift_banking77_unseen | rolling_naive | 0.10 | 0.117 | 0.25 | 0.65 | 3000 | 0.00 / 0.22 | 0.00 / 0.78 | nan / 214 |
| drift_banking77_unseen | rolling_holm | 0.02 | 0.200 | 0.16 | 1.00 | 2500 | 0.00 / 0.01 | 0.00 / 0.09 | nan / 1129 |
| drift_banking77_unseen | rolling_holm | 0.05 | 0.206 | 0.07 | 1.00 | 1500 | 0.00 / 0.00 | 0.00 / 0.03 | nan / 951 |
| drift_banking77_unseen | rolling_holm | 0.10 | 0.216 | 0.04 | 1.00 | 1000 | 0.00 / 0.00 | 0.00 / 0.01 | nan / 998 |
