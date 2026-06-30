#!/usr/bin/env bash
# Install campaign-explore MCP (z2h-explore) from GitHub.
#
# One-liner (clone + venv + ~/.cursor/mcp.json):
#   curl -fsSL https://raw.githubusercontent.com/ram-amit/z2h-explore-mcp/main/install-z2h-explore-mcp.sh | bash
#
# Already cloned:
#   ./install-z2h-explore-mcp.sh --dir .
#
# Optional env:
#   Z2H_EXPLORE_MCP_DIR       install path (default: ~/Development/z2h-explore-mcp)
#   Z2H_EXPLORE_MCP_REPO      git URL (default: git@github.com:ram-amit/z2h-explore-mcp.git)
#   Z2H_EXPLORE_MCP_TARBALL_URL   tarball URL (fallback only)
#
set -euo pipefail

DEFAULT_REPO="git@github.com:ram-amit/z2h-explore-mcp.git"
RAW_INSTALL_URL="https://raw.githubusercontent.com/ram-amit/z2h-explore-mcp/main/install-z2h-explore-mcp.sh"

INSTALL_DIR=""
REPO_URL="${Z2H_EXPLORE_MCP_REPO:-$DEFAULT_REPO}"
TARBALL_URL="${Z2H_EXPLORE_MCP_TARBALL_URL:-}"
SKIP_MCP_JSON=""

default_install_dir() {
  if [[ -n "${INSTALL_DIR:-}" ]]; then
    echo "$INSTALL_DIR"
    return
  fi
  if [[ -n "${Z2H_EXPLORE_MCP_DIR:-}" ]]; then
    echo "$Z2H_EXPLORE_MCP_DIR"
    return
  fi
  if [[ -d "$HOME/Development" ]]; then
    echo "$HOME/Development/z2h-explore-mcp"
    return
  fi
  echo "$HOME/z2h-explore-mcp"
}

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
    --skip-mcp-json)
      SKIP_MCP_JSON="--skip-mcp-json"
      shift
      ;;
    -h|--help)
      sed -n '2,14p' "$0"
      echo ""
      echo "Examples:"
      echo "  curl -fsSL $RAW_INSTALL_URL | bash"
      echo "  git clone $DEFAULT_REPO ~/Development/z2h-explore-mcp"
      echo "  cd ~/Development/z2h-explore-mcp && ./install-z2h-explore-mcp.sh --dir ."
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
BUNDLED_REPO="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"

# If this script lives inside z2h-explore-mcp, use bundled Python installer.
if [[ -f "$BUNDLED_REPO/scripts/install_mcp.py" ]]; then
  PY_INSTALLER="$BUNDLED_REPO/scripts/install_mcp.py"
else
  TARGET_DIR="$(default_install_dir)"
  if [[ ! -f "$TARGET_DIR/scripts/install_mcp.py" ]]; then
    if [[ -n "$REPO_URL" ]]; then
      echo "Cloning $REPO_URL -> $TARGET_DIR"
      mkdir -p "$(dirname "$TARGET_DIR")"
      git clone "$REPO_URL" "$TARGET_DIR"
    elif [[ -n "$TARBALL_URL" ]]; then
      echo "Tarball install requires the Python installer from the repo." >&2
      echo "Clone $DEFAULT_REPO or use: curl -fsSL $RAW_INSTALL_URL | bash" >&2
      exit 1
    else
      echo "Missing z2h-explore-mcp files." >&2
      echo "Run: curl -fsSL $RAW_INSTALL_URL | bash" >&2
      exit 1
    fi
  fi
  PY_INSTALLER="$TARGET_DIR/scripts/install_mcp.py"
  INSTALL_DIR="$TARGET_DIR"
fi

ARGS=()
[[ -n "$INSTALL_DIR" ]] && ARGS+=(--dir "$INSTALL_DIR")
[[ -n "$REPO_URL" ]] && ARGS+=(--repo-url "$REPO_URL")
[[ -n "$TARBALL_URL" ]] && ARGS+=(--tarball-url "$TARBALL_URL")
[[ -n "$SKIP_MCP_JSON" ]] && ARGS+=($SKIP_MCP_JSON)

exec python3 "$PY_INSTALLER" "${ARGS[@]}"
