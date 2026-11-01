#!/usr/bin/env bash
# Full reproducible pipeline: prepare pools (5 splits), run all experiments, diagnostics, figures.
# exp1b needs paid teacher labels first: scripts/label_with_teacher.py ... --run, then exp1b_prepare.py and run_exp1b.sh.
# Everything is logged to evidence/logs/run_all_<UTC>.log; each experiment writes a manifest.
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv/bin/activate
mkdir -p evidence/logs results
TS=$(date -u +%Y%m%dT%H%M%SZ)
exec > >(tee -a "evidence/logs/run_all_${TS}.log") 2>&1
echo "== start ${TS}"; python scripts/exp1a_prepare.py banking77,clinc150 0,1,2,3,4
for a in 0.05 0.10; do
  tag=$(echo "$a" | tr -d '.'); echo "== exp0 alpha=$a"
  cascade exp0 --alpha "$a" --trials 500 --m 200 500 1000 3000 --out results --name "exp0_alpha${tag}" > /dev/null
done
run() { # task alpha tag
  echo "== exp1a $1 alpha=$2"
  cascade exp1a data/cache/pools_$1_seed{0,1,2,3,4}.npz --alpha "$2" --delta 0.1 --trials 400 \
    --m 250 500 1000 2000 --name "exp1a_$1_alpha$3" --out results > /dev/null
}
run banking77 0.05 005; run banking77 0.03 003; run clinc150 0.02 002
echo "== exp2 drift (free; offline)"; python scripts/exp2_prepare.py banking77,clinc150 && scripts/run_exp2.sh
echo "== economics"; python scripts/make_economics.py > /dev/null || echo "economics skipped (needs cached teacher labels: scripts/label_with_teacher.py, costs money)"
echo "== diagnostics"; python scripts/diagnose_strict_sequence.py
echo "== summary + figures"; python scripts/summarize.py > /dev/null; python scripts/make_figures.py
echo "DONE ${TS}"
