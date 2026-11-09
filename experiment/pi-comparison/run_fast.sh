#!/usr/bin/env bash
# Prepare/preflight locally, then keep the real experiment in this terminal.
set -euo pipefail
FAST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAST_NAME="local-direct10-01"
FAST_TASKS=10
FAST_SPLIT=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) FAST_NAME="${2:?Missing batch name}"; shift 2 ;;
    --limit-tasks) FAST_TASKS="${2:?Missing task count}"; shift 2 ;;
    --split-final-timing) FAST_SPLIT=(--split-final-timing); shift ;;
    *) printf 'Usage: bash run_fast.sh [--name NAME] [--limit-tasks N] [--split-final-timing]\n' >&2; exit 2 ;;
  esac
done
if [[ ! "$FAST_NAME" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$ ]] || [[ ! "$FAST_TASKS" =~ ^[1-9][0-9]*$ ]]; then
  printf 'Use a simple batch name and a positive task count.\n' >&2; exit 2
fi
cd "$FAST_DIR"
if [[ ! -f "batches/$FAST_NAME/plan.json" ]]; then
  FAST_CACHE=()
  if [[ -d batches/local-aligned10-02/source-cache ]] && [[ "$FAST_TASKS" -le 10 ]]; then
    FAST_CACHE=(--source-cache batches/local-aligned10-02/source-cache)
  fi
  bash run_local.sh prepare --name "$FAST_NAME" --limit-tasks "$FAST_TASKS" --execution parallel --max-rounds 5 "${FAST_CACHE[@]}" "${FAST_SPLIT[@]}"
fi
if [[ ${#FAST_SPLIT[@]} -gt 0 ]]; then
  "${EUCLID_EXPERIMENT_PYTHON:-/Library/Frameworks/Python.framework/Versions/3.12/bin/python3}" - "$FAST_NAME" <<'PY'
import json,sys
from pathlib import Path
plan=json.loads((Path('batches')/sys.argv[1]/'plan.json').read_text())
if not plan.get('split_final_timing'):
    raise SystemExit('This existing batch does not measure final startup separately. Choose a new batch name.')
PY
fi
bash run_local.sh preflight --name "$FAST_NAME"
printf 'Direct candidates, local repair hints, five total attempts. Verifier and warm-kernel times are shown separately.\n'
if command -v caffeinate >/dev/null 2>&1; then
  exec caffeinate -i bash "$FAST_DIR/run_local.sh" resume --name "$FAST_NAME"
fi
exec bash "$FAST_DIR/run_local.sh" resume --name "$FAST_NAME"
