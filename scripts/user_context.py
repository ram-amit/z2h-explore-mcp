"""Detect local user paths and naming for MCP scaffolding."""

from __future__ import annotations

import getpass
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


def _git_config(key: str) -> str | None:
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


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "user"


def title_from_username(username: str) -> str:
    parts = re.sub(r"([a-z])([A-Z])", r"\1 \2", username).replace("_", " ").replace("-", " ").split()
    if not parts:
        return username
    return " ".join(part.capitalize() for part in parts)


def account_slug_from_identity(display_name: str, email: str | None, system_username: str) -> str:
    if email:
        local = email.split("@", 1)[0].strip().lower()
        if "." in local:
            return slugify(local.replace(".", "-"))
    if display_name:
        return slugify(display_name)
    return slugify(system_username)


@dataclass(frozen=True)
class UserContext:
    home: Path
    system_username: str
    display_name: str
    account_slug: str
    development_root: Path
    z2h_explore_mcp: Path
    cursor_mcp_json: Path
    git_email: str | None

    @property
    def campaign_explore_personal_folder(self) -> str:
        """campaign-explore bookmarks use display name, e.g. dashboards/Amit Ram/index.json"""
        return self.display_name

    def mcp_env_block(self) -> dict[str, str]:
        return {
            "Z2H_EXPLORE_PERSONAL_FOLDER": self.campaign_explore_personal_folder,
            "Z2H_EXPLORE_DEFAULT_STORAGE": "personal",
        }

    def mcp_json_entry(self, folder: Path, python_bin: Path | None = None) -> dict[str, object]:
        resolved_python = python_bin or (folder / "venv" / "bin" / "python3")
        return {
            "command": str(resolved_python),
            "args": [str(folder / "server.py")],
            "cwd": str(folder),
            "env": self.mcp_env_block(),
        }

    def mcp_json_block(self, mcp_name: str, folder: Path) -> str:
        entry = self.mcp_json_entry(folder)
        env_lines = ",\n".join(f'  "{key}": "{value}"' for key, value in entry["env"].items())
        return (
            f'"{mcp_name}": {{\n'
            f'  "command": "{entry["command"]}",\n'
            f'  "args": ["{entry["args"][0]}"],\n'
            f'  "cwd": "{entry["cwd"]}",\n'
            f'  "env": {{\n'
            f"{env_lines}\n"
            f"  }}\n"
            f"}}"
        )

    def summary(self) -> str:
        lines = [
            f"display name: {self.display_name}",
            f"account slug: {self.account_slug}",
            f"system user: {self.system_username}",
            f"home: {self.home}",
            f"development: {self.development_root}",
            f"z2h-explore-mcp: {self.z2h_explore_mcp}",
            f"mcp.json: {self.cursor_mcp_json}",
        ]
        if self.git_email:
            lines.append(f"git email: {self.git_email}")
        return "\n".join(lines)


def detect_user_context(install_dir: Path | None = None) -> UserContext:
    home = Path.home()
    system_username = getpass.getuser() or os.getenv("USER") or os.getenv("USERNAME") or "user"

    git_name = _git_config("user.name")
    git_email = _git_config("user.email")

    display_name = git_name.strip() if git_name else title_from_username(system_username)

    account_slug = account_slug_from_identity(display_name, git_email, system_username)

    development_candidates = [
        home / "Development",
        home / "dev",
        home / "Projects",
        home,
    ]
    development_root = next((path for path in development_candidates if path.is_dir()), home / "Development")

    if install_dir is not None:
        z2h_explore_mcp = install_dir.expanduser().resolve()
    else:
        script_dir = Path(__file__).resolve().parent
        z2h_explore_mcp = script_dir.parent
        if z2h_explore_mcp.name != "z2h-explore-mcp" or not (z2h_explore_mcp / "server.py").exists():
            candidate = development_root / "z2h-explore-mcp"
            z2h_explore_mcp = candidate if candidate.exists() else z2h_explore_mcp

    cursor_mcp_json = home / ".cursor" / "mcp.json"

    return UserContext(
        home=home,
        system_username=system_username,
        display_name=display_name,
        account_slug=account_slug,
        development_root=development_root,
        z2h_explore_mcp=z2h_explore_mcp,
        cursor_mcp_json=cursor_mcp_json,
        git_email=git_email,
    )
