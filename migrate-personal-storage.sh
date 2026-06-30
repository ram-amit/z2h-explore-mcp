#!/usr/bin/env bash
# Upgrade existing z2h-explore MCP to personal-folder storage (no reinstall).
#
#   cd ~/Development/z2h-explore-mcp && git pull && ./migrate-personal-storage.sh
#
# Repo: https://github.com/ram-amit/z2h-explore-mcp
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${SCRIPT_DIR}/scripts/migrate-personal-storage.py"
if [[ ! -f "$PY" ]]; then
  PY="$(dirname "$SCRIPT_DIR")/scripts/migrate-personal-storage.py"
fi
if [[ ! -f "$PY" ]]; then
  PY="./migrate-personal-storage.py"
fi
exec python3 "$PY" "$@"
