#!/usr/bin/env bash
# Read-only observer; does not launch or resume an experiment.
set -euo pipefail
MONITOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_PYTHON="${EUCLID_EXPERIMENT_PYTHON:-/Library/Frameworks/Python.framework/Versions/3.12/bin/python3}"
unset PYTHONHOME PYTHONPATH
exec "$MONITOR_PYTHON" "$MONITOR_DIR/monitor.py" "$@"
