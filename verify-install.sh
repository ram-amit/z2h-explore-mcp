#!/usr/bin/env bash
# Verify z2h-explore-mcp install + MCP client wiring.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/scripts/verify_install.py" "$@"
