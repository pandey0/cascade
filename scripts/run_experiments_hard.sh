#!/usr/bin/env bash
# Harder targets where the achievable risk is close to alpha (more informative than the easy ones).
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv/bin/activate
# wait for the main batch to finish
until grep -q "^exit=" /tmp/exp_all.log 2>/dev/null; do sleep 3; done
run() { # task alpha tag
  echo "== hard $1 alpha=$2"
  cascade exp1a data/cache/pools_$1_seed0.npz data/cache/pools_$1_seed1.npz data/cache/pools_$1_seed2.npz \
    --alpha "$2" --delta 0.1 --trials 400 --m 250 500 1000 2000 --name "exp1a_$1_alpha$3" --out results > /dev/null
}
run clinc150 0.02 002
run banking77 0.03 003
echo DONE
