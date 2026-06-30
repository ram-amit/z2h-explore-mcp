#!/usr/bin/env python3
"""Scaffold a FastMCP server using the z2h-explore-mcp layout."""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from user_context import detect_user_context, slugify  # noqa: E402

ROOT = SCRIPT_DIR.parent


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip())
    print(f"  wrote {path}")


def build_server_py(mcp_name: str, instructions: str) -> str:
    return f'''\
"""
{mcp_name} MCP server.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from api import ApiClient

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

mcp = FastMCP(
    "{mcp_name}",
    instructions={instructions!r},
)

_client: ApiClient | None = None


def client() -> ApiClient:
    global _client
    if _client is None:
        _client = ApiClient()
    return _client


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
def health_check() -> str:
    """Verify API connectivity and return basic status."""
    return _json(client().health_check())


@mcp.tool()
def list_items(search: str | None = None, limit: int = 50) -> str:
    """List items from the backing API. Use before get_item or create_item."""
    return _json(client().list_items(search=search, limit=limit))


@mcp.tool()
def get_item(item_id: str) -> str:
    """Get one item by id."""
    return _json(client().get_item(item_id))


@mcp.tool()
def create_item(name: str, payload_json: str | None = None) -> str:
    """
    Create an item. Pass optional payload_json for full control.
    Example payload_json: {{"name": "example", "enabled": true}}
    """
    payload = json.loads(payload_json) if payload_json else {{"name": name}}
    return _json(client().create_item(payload))


if __name__ == "__main__":
    mcp.run()
'''


def build_api_py() -> str:
    return '''\
"""HTTP client for the backing API."""

from __future__ import annotations

import os
from typing import Any

import httpx


class ApiClient:
    def __init__(
        self,
        base_url: str | None = None,
        auth_token: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("API_BASE_URL", "")).rstrip("/")
        if not self.base_url:
            raise ValueError("Set API_BASE_URL in .env")
        self.timeout = timeout
        headers = {"Accept": "application/json"}
        token = auth_token or os.getenv("API_AUTH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._headers = headers

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout, headers=self._headers) as client:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            if not response.content:
                return None
            return response.json()

    def health_check(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def list_items(self, *, search: str | None = None, limit: int = 50) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if search:
            params["search"] = search
        return self._request("GET", "/items", params=params)

    def get_item(self, item_id: str) -> dict[str, Any]:
        return self._request("GET", f"/items/{item_id}")

    def create_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/items", json=payload)
'''


def build_readme(ctx, mcp_name: str, folder: Path, goal: str) -> str:
    mcp_block = ctx.mcp_json_block(mcp_name, folder)
    return f'''\
# {mcp_name}

{goal}

Owner: **{ctx.display_name}** (`{ctx.account_slug}`)

## Setup

```bash
cd {folder}
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with API_BASE_URL and API_AUTH_TOKEN if needed
```

## Cursor

Add to `{ctx.cursor_mcp_json}`:

```json
{mcp_block}
```

Restart Cursor.

## Tools

| Tool | Purpose |
|------|---------|
| `health_check` | Verify API connectivity |
| `list_items` | Discover items before read/write |
| `get_item` | Fetch one item |
| `create_item` | Create with name or full JSON payload |

## Example prompts

- "Use {mcp_name} health_check to verify the API works"
- "List items from {mcp_name} matching weekly report"
- "Create a test item named [TEST] scaffold check"

## Customize

1. Replace stub endpoints in `api.py` with your real API paths
2. Add domain-specific tools in `server.py`
3. See `{ctx.z2h_explore_mcp}` for a full production example (campaign-explore)

## campaign-explore personal folder

If this MCP writes to campaign-explore, pin items under:

- `dashboards/{ctx.campaign_explore_personal_folder}/index.json`
- `looks/{ctx.campaign_explore_personal_folder}/index.json`

## Reference

- Personalized paste prompt: `{ctx.z2h_explore_mcp}/templates/PASTE_TO_CREATE_MCP.md`
- Regenerate after switching machines: `python3 {ctx.z2h_explore_mcp}/scripts/personalize_prompt.py`
'''


def maybe_print_mcp_json_merge_hint(ctx, mcp_name: str, folder: Path) -> None:
    config_path = ctx.cursor_mcp_json
    block = ctx.mcp_json_block(mcp_name, folder)
    print(f"\nAdd to {config_path}:\n")
    print(block)
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text())
            if mcp_name in existing:
                print(f"\nNote: '{mcp_name}' already exists in mcp.json — merge or rename if needed.")
        except json.JSONDecodeError:
            print("\nNote: mcp.json exists but is not valid JSON — merge manually.")


def main() -> None:
    ctx = detect_user_context()

    parser = argparse.ArgumentParser(description="Scaffold a FastMCP server for the current user")
    parser.add_argument("--name", help="MCP name (kebab-case). Default: <account-slug>-mcp")
    parser.add_argument("--folder", help="Folder name under Development (default: same as --name)")
    parser.add_argument("--goal", default="MCP for internal API workflows.", help="One-line description")
    parser.add_argument("--instructions", default="", help="Agent instructions shown in MCP metadata")
    parser.add_argument(
        "--development-root",
        type=Path,
        default=None,
        help=f"Override Development folder (default: {ctx.development_root})",
    )
    args = parser.parse_args()

    development_root = args.development_root or ctx.development_root
    mcp_name = args.name or f"{ctx.account_slug}-mcp"
    folder_name = args.folder or mcp_name
    target = development_root / folder_name

    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty folder: {target}")

    instructions = args.instructions or (
        f"MCP for {ctx.display_name}. {args.goal} Use list_items before get_item or create_item."
    )

    print(f"Detected:\n{ctx.summary()}\n")
    print(f"Scaffolding {mcp_name} -> {target}")
    write_file(target / "requirements.txt", "mcp[cli]>=1.9.0\npython-dotenv>=1.0.0\nhttpx>=0.27.0\n")
    write_file(
        target / ".env.example",
        "API_BASE_URL=https://your-api.example.com\n# API_AUTH_TOKEN=\n",
    )
    write_file(target / ".gitignore", "venv/\n.env\n__pycache__/\n*.pyc\n")
    write_file(target / "api.py", build_api_py())
    write_file(target / "server.py", build_server_py(mcp_name, instructions))
    write_file(target / "README.md", build_readme(ctx, mcp_name, target, args.goal))

    maybe_print_mcp_json_merge_hint(ctx, mcp_name, target)

    print("\nDone. Next:")
    print(f"  cd {target} && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt")
    print("  Edit api.py + server.py for your API")
    print(f"  python3 {ctx.z2h_explore_mcp}/scripts/personalize_prompt.py")
    print("  Paste templates/PASTE_TO_CREATE_MCP.md into Cursor to finish with the agent")


if __name__ == "__main__":
    main()
