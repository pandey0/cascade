#!/usr/bin/env bash
# Install CPU-only torch + bench extras, then prepare pools. Logs to /tmp/exp1a_setup.log
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv/bin/activate
echo "== install torch (CPU)"; pip install -q torch --index-url https://download.pytorch.org/whl/cpu
echo "== install bench extras"; pip install -q -e ".[bench]"
echo "== prepare"; python scripts/exp1a_prepare.py banking77,clinc150
echo "DONE"
