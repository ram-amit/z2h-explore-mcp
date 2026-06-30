"""Merge z2h-explore into Cursor / Claude Code / Claude Desktop MCP config files."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

MCP_KEY = "z2h-explore"


def load_json_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected JSON shape in {path}")
    return data


def get_mcp_servers(config: dict[str, Any]) -> dict[str, Any]:
    if "mcpServers" in config and isinstance(config["mcpServers"], dict):
        return config["mcpServers"]
    return {k: v for k, v in config.items() if k != "mcpServers" and isinstance(v, dict)}


def merge_mcp_server_config(
    config_path: Path,
    entry: dict[str, object],
    *,
    label: str,
) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        try:
            config = load_json_config(config_path)
        except ValueError:
            backup = config_path.with_suffix(config_path.suffix + ".bak")
            shutil.copy2(config_path, backup)
            print(f"Backed up invalid {label} config to {backup}")
            config = {}
    else:
        config = {}

    servers = get_mcp_servers(config)
    servers[MCP_KEY] = entry
    config["mcpServers"] = servers
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"Updated {label} config: {config_path}")


def claude_code_config_path(home: Path) -> Path:
    return home / ".claude.json"


def claude_desktop_config_path(home: Path) -> Path | None:
    if home.name == "Users" or (home / "Library").exists():
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return None


def cursor_is_available(home: Path) -> bool:
    return (home / ".cursor").exists() or shutil.which("cursor") is not None


def claude_code_cli_available() -> bool:
    return shutil.which("claude") is not None


def detect_default_clients(home: Path) -> str:
    env_override = os.getenv("Z2H_EXPLORE_CLIENTS")
    if env_override:
        return env_override

    has_cursor = cursor_is_available(home)
    has_claude = claude_code_cli_available()

    if has_claude and not has_cursor:
        return "claude-code"
    if has_cursor and not has_claude:
        return "cursor"
    if has_claude and has_cursor:
        return "cursor"
    if has_claude:
        return "claude-code"
    return "cursor"


def register_claude_code_cli(
    install_dir: Path,
    python_bin: Path,
    env: dict[str, str],
) -> bool:
    claude_bin = shutil.which("claude")
    if not claude_bin:
        return False

    subprocess.run(
        [claude_bin, "mcp", "remove", MCP_KEY, "-s", "user"],
        capture_output=True,
        text=True,
        check=False,
    )

    cmd: list[str] = [claude_bin, "mcp", "add", MCP_KEY, "-s", "user"]
    for key, value in env.items():
        cmd.extend(["-e", f"{key}={value}"])
    cmd.extend(["--", str(python_bin), str(install_dir / "server.py")])

    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()
        print(f"WARN: `claude mcp add` failed: {detail}")
        return False

    print("Registered z2h-explore via Claude Code CLI (`claude mcp add -s user`)")
    return True
