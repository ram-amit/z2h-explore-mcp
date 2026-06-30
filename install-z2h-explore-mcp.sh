#!/usr/bin/env bash
# Install campaign-explore MCP (z2h-explore) from GitHub.
#
# Recommended (copy/paste exactly):
#   git clone https://github.com/ram-amit/z2h-explore-mcp.git ~/z2h-explore-mcp && cd ~/z2h-explore-mcp && ./install-z2h-explore-mcp.sh --dir .
#
# Already cloned:
#   ./install-z2h-explore-mcp.sh --dir .
#
# Claude Desktop instead of Cursor:
#   ./install-z2h-explore-mcp.sh --dir . --clients claude
#
# Both clients:
#   ./install-z2h-explore-mcp.sh --dir . --clients both
#
set -euo pipefail

DEFAULT_REPO="https://github.com/ram-amit/z2h-explore-mcp.git"

INSTALL_DIR=""
REPO_URL="${Z2H_EXPLORE_MCP_REPO:-$DEFAULT_REPO}"
TARBALL_URL="${Z2H_EXPLORE_MCP_TARBALL_URL:-}"
SKIP_MCP_JSON=""
CLIENTS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --repo-url)
      REPO_URL="$2"
      shift 2
      ;;
    --tarball-url)
      TARBALL_URL="$2"
      shift 2
      ;;
    --clients)
      CLIENTS="$2"
      shift 2
      ;;
    --skip-mcp-json)
      SKIP_MCP_JSON="--skip-mcp-json"
      shift
      ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

default_install_dir() {
  if [[ -n "${INSTALL_DIR:-}" ]]; then echo "$INSTALL_DIR"; return; fi
  if [[ -n "${Z2H_EXPLORE_MCP_DIR:-}" ]]; then echo "$Z2H_EXPLORE_MCP_DIR"; return; fi
  echo "$HOME/z2h-explore-mcp"
}

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
BUNDLED_REPO="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"

if [[ -f "$BUNDLED_REPO/scripts/install_mcp.py" ]]; then
  PY_INSTALLER="$BUNDLED_REPO/scripts/install_mcp.py"
else
  TARGET_DIR="$(default_install_dir)"
  if [[ ! -f "$TARGET_DIR/scripts/install_mcp.py" ]]; then
    echo "Cloning $REPO_URL -> $TARGET_DIR"
    mkdir -p "$(dirname "$TARGET_DIR")"
    git clone "$REPO_URL" "$TARGET_DIR"
  fi
  PY_INSTALLER="$TARGET_DIR/scripts/install_mcp.py"
  INSTALL_DIR="$TARGET_DIR"
fi

ARGS=()
[[ -n "$INSTALL_DIR" ]] && ARGS+=(--dir "$INSTALL_DIR")
[[ -n "$REPO_URL" ]] && ARGS+=(--repo-url "$REPO_URL")
[[ -n "$TARBALL_URL" ]] && ARGS+=(--tarball-url "$TARBALL_URL")
[[ -n "$SKIP_MCP_JSON" ]] && ARGS+=($SKIP_MCP_JSON)
[[ -n "$CLIENTS" ]] && ARGS+=(--clients "$CLIENTS")

# Prefer Homebrew / newer python for the installer bootstrap when available
BOOTSTRAP_PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3.10 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    BOOTSTRAP_PYTHON="$(command -v "$candidate")"
    break
  fi
  if [[ -x "$candidate" ]]; then
    BOOTSTRAP_PYTHON="$candidate"
    break
  fi
done

if [[ -z "$BOOTSTRAP_PYTHON" ]]; then
  echo "python3 not found" >&2
  exit 1
fi

exec "$BOOTSTRAP_PYTHON" "$PY_INSTALLER" "${ARGS[@]}"
