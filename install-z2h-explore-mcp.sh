#!/usr/bin/env bash
# Install campaign-explore MCP (z2h-explore) — single script for the team.
#
# Usage:
#   curl -fsSL "<URL>/install-z2h-explore-mcp.sh" | bash
#   ./install-z2h-explore-mcp.sh
#   ./install-z2h-explore-mcp.sh --dir ~/Desktop/z2h-explore-mcp
#
# Optional env:
#   Z2H_EXPLORE_MCP_DIR       install path (same as --dir)
#   Z2H_EXPLORE_MCP_REPO      git URL to clone if folder missing
#   Z2H_EXPLORE_MCP_TARBALL_URL   tarball URL to download if folder missing
#
set -euo pipefail

INSTALL_DIR=""
REPO_URL="${Z2H_EXPLORE_MCP_REPO:-}"
TARBALL_URL="${Z2H_EXPLORE_MCP_TARBALL_URL:-}"
SKIP_MCP_JSON=""

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
  # Bootstrap: download repo via git/tarball into a temp copy of install_mcp.py path
  TARGET_DIR="${INSTALL_DIR:-${Z2H_EXPLORE_MCP_DIR:-$HOME/z2h-explore-mcp}}"
  if [[ ! -f "$TARGET_DIR/scripts/install_mcp.py" ]]; then
    if [[ -n "$REPO_URL" ]]; then
      echo "Cloning $REPO_URL -> $TARGET_DIR"
      git clone "$REPO_URL" "$TARGET_DIR"
    elif [[ -n "$TARBALL_URL" ]]; then
      echo "Download tarball from Z2H_EXPLORE_MCP_TARBALL_URL not supported in pure bash."
      echo "Re-run after clone, or use the Python installer from the repo."
      exit 1
    else
      echo "Missing z2h-explore-mcp files." >&2
      echo "Set Z2H_EXPLORE_MCP_REPO, pass --repo-url, or unzip the shared folder and run from inside it." >&2
      exit 1
    fi
  fi
  PY_INSTALLER="$TARGET_DIR/scripts/install_mcp.py"
fi

ARGS=()
[[ -n "$INSTALL_DIR" ]] && ARGS+=(--dir "$INSTALL_DIR")
[[ -n "$REPO_URL" ]] && ARGS+=(--repo-url "$REPO_URL")
[[ -n "$TARBALL_URL" ]] && ARGS+=(--tarball-url "$TARBALL_URL")
[[ -n "$SKIP_MCP_JSON" ]] && ARGS+=($SKIP_MCP_JSON)

exec python3 "$PY_INSTALLER" "${ARGS[@]}"
