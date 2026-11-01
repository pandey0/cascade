# Evidence log
- `ledger.csv`: one line per recorded run (time, command, code hash, wall time, manifest).
- `manifests/*.json`: command, code state (commit if any + source-tree hash), environment, input/output SHA-256, parameters.
- `logs/`: raw stdout of every pipeline run (`v1_*` = first, 5-method, 3-split runs; `run_all_*` = current).
- `diagnostics/`: data behind specific findings (e.g., the strict-sequence pitfall).
- `screenshots/`: only for things that are visual (dashboards, Colab runs, GitHub pages). Name `YYYYMMDD-what.png`, and note in `NOTES.md` what each shows and how to reproduce it. For numbers, prefer generated figures/tables.
Rule: no number goes into the paper unless it traces to a file here or in `results/`.
