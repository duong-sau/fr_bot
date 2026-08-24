#!/usr/bin/env bash
set -euo pipefail

# Launch the interactive fr_bot config/API-key menu (Tools/manage_config.py).
# Works both on the deployed Ubuntu host (venv at $APP_ROOT/venv) and locally
# (falls back to python3/python on PATH).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="${APP_ROOT:-/home/ubuntu/fr_bot}"
VENV_DIR="${VENV_DIR:-$APP_ROOT/venv}"

# Probe each candidate with --version rather than just `command -v`, since on
# Windows `python`/`python3` can resolve to a non-functional WindowsApps stub
# that "exists" on PATH but exits with an error when actually invoked.
PYTHON=""
for candidate in "$VENV_DIR/bin/python" python python3; do
  if "$candidate" --version >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done

if [[ -z "$PYTHON" ]]; then
  echo "[ERROR] No working python interpreter found (checked $VENV_DIR/bin/python, python, python3)." >&2
  exit 1
fi

exec "$PYTHON" "$SCRIPT_DIR/Tools/manage_config.py" "$@"
