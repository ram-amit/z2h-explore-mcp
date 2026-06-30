#!/usr/bin/env bash
# One command: generate your ready-to-paste Cursor prompt.
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$DIR/scripts/personalize_prompt.py" "$@"
