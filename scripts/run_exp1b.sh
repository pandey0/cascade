#!/usr/bin/env bash
# exp1b: gates with a noisy LLM teacher (Claude Haiku 5.5 labels). Needs scripts/exp1b_prepare.py first.
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv/bin/activate
mkdir -p evidence/logs results
for task in banking77 clinc150; do for variant in distilled goldtrained; do for a in 0.05 0.10; do
  tag=$(echo "$a" | tr -d '.')
  echo "== exp1b $task $variant alpha=$a"
  cascade exp1b data/cache/pools1b_${variant}_${task}_seed{0,1,2}.npz --alpha "$a" --delta 0.1 \
    --trials 400 --m 100 200 400 --name "exp1b_${variant}_${task}_alpha${tag}" --out results > /dev/null
done; done; done
echo DONE
