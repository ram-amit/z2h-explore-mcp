#!/usr/bin/env python3
"""Verify a z2h-explore-mcp install and MCP client wiring."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from mcp_config import MCP_KEY, claude_desktop_config_path, load_json_config  # noqa: E402
from install_mcp import MIN_PYTHON, find_python, python_is_supported, resolve_install_dir  # noqa: E402

OK = "ok"
WARN = "warn"
FAIL = "fail"


def check(label: str, status: str, detail: str) -> tuple[str, str, str]:
    icon = {"ok": "OK", "warn": "WARN", "fail": "FAIL"}[status]
    print(f"[{icon}] {label}: {detail}")
    return label, status, detail


def resolve_install_from_args() -> Path:
    install_dir = resolve_install_dir(sys.argv[1] if len(sys.argv) > 1 else None)
    if not (install_dir / "server.py").exists():
        raise SystemExit(f"Not a z2h-explore-mcp install: {install_dir}")
    return install_dir


def has_mcp_entry(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        config = load_json_config(path)
    except ValueError:
        return False
    servers = config.get("mcpServers", config)
    return isinstance(servers, dict) and MCP_KEY in servers


def main() -> int:
    install_dir = resolve_install_from_args()
    home = Path.home()
    results: list[tuple[str, str, str]] = []

    venv_python = install_dir / "venv" / "bin" / "python3"
    if venv_python.exists() and python_is_supported(str(venv_python)):
        results.append(check("venv", OK, str(venv_python)))
    else:
        results.append(check("venv", FAIL, f"missing or Python < {MIN_PYTHON[0]}.{MIN_PYTHON[1]} at {venv_python}"))

    try:
        system_python = find_python()
        results.append(check("system python", OK, system_python))
    except SystemExit as exc:
        results.append(check("system python", FAIL, str(exc)))

    env_path = install_dir / ".env"
    if env_path.exists():
        results.append(check(".env", OK, str(env_path)))
    else:
        results.append(check(".env", WARN, "missing; re-run installer"))

    cursor_path = home / ".cursor" / "mcp.json"
    if has_mcp_entry(cursor_path):
        results.append(check("cursor mcp", OK, str(cursor_path)))
    else:
        results.append(check("cursor mcp", WARN, f"'{MCP_KEY}' not in {cursor_path}"))

    claude_path = claude_desktop_config_path(home)
    if claude_path:
        if has_mcp_entry(claude_path):
            results.append(check("claude desktop mcp", OK, str(claude_path)))
        else:
            results.append(check("claude desktop mcp", WARN, f"'{MCP_KEY}' not in {claude_path}"))

    if venv_python.exists():
        try:
            subprocess.run(
                [str(venv_python), "-c", "import mcp, httpx; print('imports ok')"],
                check=True,
                capture_output=True,
                text=True,
            )
            results.append(check("python packages", OK, "mcp + httpx importable"))
        except subprocess.CalledProcessError as exc:
            results.append(check("python packages", FAIL, exc.stderr or "import failed"))

        try:
            result = subprocess.run(
                [
                    str(venv_python),
                    "-c",
                    "from explores import EXPLORES; print(len(EXPLORES))",
                ],
                check=True,
                cwd=install_dir,
                capture_output=True,
                text=True,
            )
            results.append(check("server module", OK, f"{result.stdout.strip()} explores registered"))
        except subprocess.CalledProcessError as exc:
            results.append(check("server module", FAIL, exc.stderr or "import failed"))

    failed = [name for name, status, _ in results if status == FAIL]
    print()
    if failed:
        print("Fix failures, then re-run: ./install-z2h-explore-mcp.sh --dir .")
        print("Or: python3 scripts/verify_install.py")
        return 1

    print("Install looks good.")
    print("Restart Cursor (or Claude Desktop), then ask:")
    print('  list explores in campaign-explore')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
