#!/usr/bin/env bash
# Re-run experiment 0 (synthetic) and 1a (real pools, gold labels as teacher) with all five gates.
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv/bin/activate
for a in 0.05 0.10; do
  tag=$(echo "$a" | tr -d '.')
  echo "== exp0 alpha=$a"
  cascade exp0 --alpha "$a" --trials 500 --m 200 500 1000 3000 --out results --name_unused 2>/dev/null || \
  cascade exp0 --alpha "$a" --trials 500 --m 200 500 1000 3000 --out "results/_exp0_$tag"
  mv "results/_exp0_$tag/exp0.md" "results/exp0_alpha$tag.md"; mv "results/_exp0_$tag/exp0.json" "results/exp0_alpha$tag.json"; rmdir "results/_exp0_$tag"
  for task in banking77 clinc150; do
    echo "== exp1a $task alpha=$a"
    cascade exp1a data/cache/pools_${task}_seed0.npz data/cache/pools_${task}_seed1.npz data/cache/pools_${task}_seed2.npz \
      --alpha "$a" --delta 0.1 --trials 400 --m 250 500 1000 2000 --name "exp1a_${task}_alpha$tag" --out results > /dev/null
  done
done
echo DONE
