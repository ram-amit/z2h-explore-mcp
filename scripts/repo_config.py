"""Canonical GitHub repo URLs for installs and docs."""

from __future__ import annotations

GITHUB_OWNER = "ram-amit"
GITHUB_REPO = "z2h-explore-mcp"
DEFAULT_BRANCH = "main"

DEFAULT_REPO_SSH = f"git@github.com:{GITHUB_OWNER}/{GITHUB_REPO}.git"
DEFAULT_REPO_HTTPS = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}.git"
GITHUB_WEB_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
RAW_INSTALL_SCRIPT_URL = (
    f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{DEFAULT_BRANCH}/install-z2h-explore-mcp.sh"
)
DEFAULT_INSTALL_DIRNAME = "z2h-explore-mcp"
