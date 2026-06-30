"""Merge z2h-explore into Cursor / Claude Desktop MCP config files."""

from __future__ import annotations

import json
import shutil
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


def claude_desktop_config_path(home: Path) -> Path | None:
    if home.name == "Users" or (home / "Library").exists():
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return None
