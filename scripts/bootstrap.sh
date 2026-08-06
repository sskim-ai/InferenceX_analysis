#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

"${PYTHON_BIN}" -m venv "${ROOT}/.venv"
"${ROOT}/.venv/bin/python" -m pip install --upgrade pip
"${ROOT}/.venv/bin/python" -m pip install -e "${ROOT}[dev]"
"${ROOT}/.venv/bin/python" -m pip freeze | LC_ALL=C sort | sed "s|^-e ${ROOT}$|-e .|" > "${ROOT}/requirements.lock"

echo "Bootstrap complete: ${ROOT}/.venv"
