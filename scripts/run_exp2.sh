#!/usr/bin/env bash
# exp2: drift streams. Needs scripts/exp2_prepare.py first. Gold-label teacher (isolates drift).
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv/bin/activate
mkdir -p evidence/logs results
for w in 300 1000; do
  cascade exp2 data/cache/drift_banking77_{prior,perturbed,unseen}.npz --alpha 0.05 --trials 100 \
    --window "$w" --name "exp2_banking77_w${w}" --out results > /dev/null
  cascade exp2 data/cache/drift_clinc150_{prior,perturbed,unseen}.npz --alpha 0.02 --trials 100 \
    --window "$w" --name "exp2_clinc150_w${w}" --out results > /dev/null
done
echo DONE
