alpha=0.05, delta=0.1, 100 streams per cell, 3000 pre + 6000 post decisions, window 1000 labels.

| pool | policy | audit | post risk | post cov | block viol | recovery (decisions) | false alarm CS / z | detect CS / z | delay CS / z |
|---|---|---|---|---|---|---|---|---|---|
| drift_banking77_prior | static_holm | 0.02 | 0.055 | 0.87 | 0.65 | 1000 | 0.00 / 0.01 | 0.00 / 0.03 | nan / 484 |
| drift_banking77_prior | static_holm | 0.05 | 0.055 | 0.87 | 0.65 | 1000 | 0.00 / 0.02 | 0.00 / 0.16 | nan / 4013 |
| drift_banking77_prior | static_holm | 0.10 | 0.055 | 0.87 | 0.65 | 1000 | 0.00 / 0.02 | 0.00 / 0.34 | nan / 3049 |
| drift_banking77_prior | rolling_naive | 0.02 | 0.071 | 0.91 | 0.91 | inf | 0.00 / 0.03 | 0.00 / 0.14 | nan / 3619 |
| drift_banking77_prior | rolling_naive | 0.05 | 0.067 | 0.90 | 0.87 | 5000 | 0.00 / 0.04 | 0.00 / 0.45 | nan / 3574 |
| drift_banking77_prior | rolling_naive | 0.10 | 0.064 | 0.89 | 0.82 | 4000 | 0.00 / 0.07 | 0.00 / 0.66 | nan / 1890 |
| drift_banking77_prior | rolling_holm | 0.02 | 0.044 | 0.83 | 0.33 | 500 | 0.00 / 0.01 | 0.00 / 0.00 | nan / nan |
| drift_banking77_prior | rolling_holm | 0.05 | 0.042 | 0.82 | 0.26 | 500 | 0.00 / 0.01 | 0.00 / 0.02 | nan / 4702 |
| drift_banking77_prior | rolling_holm | 0.10 | 0.040 | 0.81 | 0.21 | 500 | 0.00 / 0.01 | 0.00 / 0.05 | nan / 2036 |
| drift_banking77_perturbed | static_holm | 0.02 | 0.047 | 0.79 | 0.39 | 500 | 0.00 / 0.01 | 0.00 / 0.06 | nan / 3348 |
| drift_banking77_perturbed | static_holm | 0.05 | 0.047 | 0.79 | 0.39 | 500 | 0.00 / 0.02 | 0.00 / 0.11 | nan / 3807 |
| drift_banking77_perturbed | static_holm | 0.10 | 0.047 | 0.79 | 0.39 | 500 | 0.00 / 0.02 | 0.00 / 0.09 | nan / 2936 |
| drift_banking77_perturbed | rolling_naive | 0.02 | 0.063 | 0.84 | 0.78 | 3000 | 0.00 / 0.03 | 0.00 / 0.19 | nan / 2256 |
| drift_banking77_perturbed | rolling_naive | 0.05 | 0.061 | 0.83 | 0.75 | 2500 | 0.00 / 0.04 | 0.00 / 0.32 | nan / 3722 |
| drift_banking77_perturbed | rolling_naive | 0.10 | 0.059 | 0.83 | 0.73 | 2250 | 0.00 / 0.07 | 0.00 / 0.49 | nan / 2818 |
| drift_banking77_perturbed | rolling_holm | 0.02 | 0.036 | 0.75 | 0.14 | 500 | 0.00 / 0.01 | 0.00 / 0.02 | nan / 2999 |
| drift_banking77_perturbed | rolling_holm | 0.05 | 0.036 | 0.75 | 0.12 | 500 | 0.00 / 0.01 | 0.00 / 0.00 | nan / nan |
| drift_banking77_perturbed | rolling_holm | 0.10 | 0.035 | 0.75 | 0.12 | 500 | 0.00 / 0.01 | 0.00 / 0.03 | nan / 3437 |
| drift_banking77_unseen | static_holm | 0.02 | 0.359 | 0.70 | 1.00 | inf | 0.00 / 0.02 | 0.23 / 0.97 | 4539 / 1413 |
| drift_banking77_unseen | static_holm | 0.05 | 0.359 | 0.70 | 1.00 | inf | 0.00 / 0.01 | 0.76 / 0.99 | 4099 / 753 |
| drift_banking77_unseen | static_holm | 0.10 | 0.359 | 0.70 | 1.00 | inf | 0.00 / 0.05 | 0.97 / 0.95 | 3457 / 432 |
| drift_banking77_unseen | rolling_naive | 0.02 | 0.350 | 0.69 | 1.00 | inf | 0.00 / 0.02 | 0.21 / 0.98 | 4771 / 908 |
| drift_banking77_unseen | rolling_naive | 0.05 | 0.290 | 0.60 | 1.00 | inf | 0.00 / 0.07 | 0.51 / 0.93 | 4372 / 485 |
| drift_banking77_unseen | rolling_naive | 0.10 | 0.221 | 0.49 | 0.99 | inf | 0.00 / 0.17 | 0.36 / 0.83 | 3225 / 238 |
| drift_banking77_unseen | rolling_holm | 0.02 | 0.275 | 0.58 | 1.00 | inf | 0.00 / 0.02 | 0.00 / 0.97 | nan / 1714 |
| drift_banking77_unseen | rolling_holm | 0.05 | 0.210 | 0.46 | 0.98 | inf | 0.00 / 0.01 | 0.00 / 0.99 | nan / 1081 |
| drift_banking77_unseen | rolling_holm | 0.10 | 0.158 | 0.29 | 0.83 | 4500 | 0.00 / 0.01 | 0.00 / 0.99 | nan / 586 |
