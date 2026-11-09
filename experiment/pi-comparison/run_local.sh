#!/usr/bin/env bash
# Use the workstation interpreter validated by the offline regression suite.
# Workers, task runners and tool brokers inherit it through sys.executable.
set -euo pipefail
EXPERIMENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPERIMENT_PYTHON="${EUCLID_EXPERIMENT_PYTHON:-/Library/Frameworks/Python.framework/Versions/3.12/bin/python3}"
if [[ ! -x "$EXPERIMENT_PYTHON" ]]; then
  printf 'Python unavailable: %s\nSet EUCLID_EXPERIMENT_PYTHON to an interpreter with the experiment dependencies.\n' "$EXPERIMENT_PYTHON" >&2
  exit 2
fi
# Avoid injecting a different environment's Python libraries into this process tree.
unset PYTHONHOME PYTHONPATH
if ! "$EXPERIMENT_PYTHON" -c 'import pdfplumber' >/dev/null 2>&1; then
  printf 'Missing pdfplumber in %s. Choose the validated Python environment.\n' "$EXPERIMENT_PYTHON" >&2
  exit 2
fi
printf 'Experiment Python: %s\n' "$EXPERIMENT_PYTHON" >&2
cd "$EXPERIMENT_DIR"
if [[ $# -eq 0 ]]; then set -- --help; fi
exec "$EXPERIMENT_PYTHON" "$EXPERIMENT_DIR/runtime/batch.py" "$@"
