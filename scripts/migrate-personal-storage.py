#!/usr/bin/env python3
"""
One-shot upgrade: personal-folder defaults for z2h-explore MCP.

Run locally (no new folder to unzip). Finds your existing install from
~/.cursor/mcp.json, pulls latest code if git repo, writes .env, updates mcp.json env.

Usage:
  python3 migrate-personal-storage.py
  python3 migrate-personal-storage.py --install-dir ~/Development/z2h-explore-mcp
  python3 migrate-personal-storage.py --dry-run

Share with teammates: `cd ~/Development/z2h-explore-mcp && git pull && ./migrate-personal-storage.sh`
Repo: https://github.com/ram-amit/z2h-explore-mcp
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from repo_config import GITHUB_WEB_URL

MCP_KEY = "z2h-explore"
MARKER = "def personal_folder_name()"


def git_config(key: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "config", "--global", key],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    value = result.stdout.strip()
    return value or None


def detect_personal_folder() -> str:
    name = git_config("user.name")
    if name:
        return name.strip()
    import getpass

    fallback = getpass.getuser() or "user"
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", fallback).replace("_", " ").replace("-", " ").title()


def load_mcp_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"mcp.json not found: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Unexpected mcp.json shape in {path}")
    return data


def get_servers(config: dict) -> dict:
    if "mcpServers" in config and isinstance(config["mcpServers"], dict):
        return config["mcpServers"]
    return {k: v for k, v in config.items() if k != "mcpServers" and isinstance(v, dict)}


def resolve_install_dir(explicit: str | None, servers: dict) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    entry = servers.get(MCP_KEY)
    if not isinstance(entry, dict):
        raise SystemExit(
            f"'{MCP_KEY}' not found in ~/.cursor/mcp.json. Install z2h-explore first."
        )
    for key in ("cwd",):
        raw = entry.get(key)
        if raw:
            path = Path(str(raw)).expanduser().resolve()
            if (path / "server.py").exists():
                return path
    args = entry.get("args") or []
    for arg in args:
        path = Path(str(arg)).expanduser().resolve()
        if path.name == "server.py" and path.exists():
            return path.parent
    command = entry.get("command")
    if command:
        cmd_path = Path(str(command)).expanduser().resolve()
        if cmd_path.parent.name == "bin" and (cmd_path.parent.parent / "server.py").exists():
            return cmd_path.parent.parent.resolve()
    raise SystemExit(
        "Could not resolve z2h-explore install dir from mcp.json. Pass --install-dir."
    )


def has_personal_storage_code(install_dir: Path) -> bool:
    api_py = install_dir / "api.py"
    if not api_py.exists():
        return False
    return MARKER in api_py.read_text()


def git_pull(install_dir: Path, dry_run: bool) -> None:
    if not (install_dir / ".git").exists():
        print(f"No git repo at {install_dir} (skipping git pull)")
        return
    cmd = ["git", "pull", "--ff-only"]
    if dry_run:
        print(f"[dry-run] would run: {' '.join(cmd)} in {install_dir}")
        return
    print(f"Pulling latest code in {install_dir} ...")
    subprocess.run(cmd, cwd=install_dir, check=True)


def write_env(install_dir: Path, personal_folder: str, dry_run: bool) -> Path:
    env_path = install_dir / ".env"
    body = (
        f"Z2H_EXPLORE_PERSONAL_FOLDER={personal_folder}\n"
        "Z2H_EXPLORE_DEFAULT_STORAGE=personal\n"
    )
    if dry_run:
        print(f"[dry-run] would write {env_path}:\n{body}")
        return env_path
    env_path.write_text(body)
    print(f"Wrote {env_path}")
    return env_path


def merge_mcp_entry(entry: dict, personal_folder: str) -> dict:
    updated = dict(entry)
    env = dict(updated.get("env") or {})
    env["Z2H_EXPLORE_PERSONAL_FOLDER"] = personal_folder
    env["Z2H_EXPLORE_DEFAULT_STORAGE"] = "personal"
    updated["env"] = env
    return updated


def update_mcp_json(mcp_path: Path, personal_folder: str, dry_run: bool) -> None:
    config = load_mcp_json(mcp_path)
    servers = get_servers(config)
    if MCP_KEY not in servers:
        raise SystemExit(f"'{MCP_KEY}' not in {mcp_path}")
    servers[MCP_KEY] = merge_mcp_entry(servers[MCP_KEY], personal_folder)
    if "mcpServers" in config:
        config["mcpServers"] = servers
    else:
        config.clear()
        config["mcpServers"] = servers
    if dry_run:
        print(f"[dry-run] would update {mcp_path} env for {MCP_KEY}")
        print(json.dumps(servers[MCP_KEY], indent=2))
        return
    backup = mcp_path.with_suffix(".json.bak")
    shutil.copy2(mcp_path, backup)
    mcp_path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"Updated {mcp_path} (backup: {backup})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upgrade z2h-explore MCP to personal-folder storage defaults"
    )
    parser.add_argument(
        "--install-dir",
        help="z2h-explore-mcp folder (default: read from ~/.cursor/mcp.json)",
    )
    parser.add_argument(
        "--mcp-json",
        default=str(Path.home() / ".cursor" / "mcp.json"),
        help="Path to Cursor mcp.json",
    )
    parser.add_argument(
        "--personal-folder",
        help="Override personal folder name (default: git config user.name)",
    )
    parser.add_argument(
        "--skip-git-pull",
        action="store_true",
        help="Do not run git pull in install dir",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    mcp_path = Path(args.mcp_json).expanduser()
    config = load_mcp_json(mcp_path)
    servers = get_servers(config)
    install_dir = resolve_install_dir(args.install_dir, servers)
    personal_folder = (args.personal_folder or detect_personal_folder()).strip()

    print(f"Install dir:      {install_dir}")
    print(f"Personal folder:  {personal_folder}")
    print(f"mcp.json:         {mcp_path}")

    if not args.skip_git_pull:
        git_pull(install_dir, args.dry_run)

    if not has_personal_storage_code(install_dir):
        raise SystemExit(
            "\napi.py is missing personal-storage support (old MCP code).\n"
            f"Fix: cd {install_dir} && git pull\n"
            f"Or clone latest from {GITHUB_WEB_URL}, then re-run this script.\n"
        )

    write_env(install_dir, personal_folder, args.dry_run)
    update_mcp_json(mcp_path, personal_folder, args.dry_run)

    print("\nDone. Restart Cursor.")
    print(f'Looks/dashboards will save under looks/{personal_folder}/ and dashboards/{personal_folder}/')


if __name__ == "__main__":
    main()
