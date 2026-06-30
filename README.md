# Z2H Explore MCP

Repo: https://github.com/ram-amit/z2h-explore-mcp

MCP server for creating and managing **looks** and **dashboards** in [campaign-explore](https://bigbrain.me/bigbrain-vibe/campaign-explore) on bigbrain.me. Intended as the Z2H replacement for Looker MCP after Looker sunset.

## Setup

```bash
cd ~/Development/z2h-explore-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional
```

Add to `~/.cursor/mcp.json`:

```json
"z2h-explore": {
  "command": "/Users/amitram/Development/z2h-explore-mcp/venv/bin/python3",
  "args": ["/Users/amitram/Development/z2h-explore-mcp/server.py"],
  "cwd": "/Users/amitram/Development/z2h-explore-mcp",
  "env": {
    "Z2H_EXPLORE_PERSONAL_FOLDER": "Amit Ram",
    "Z2H_EXPLORE_DEFAULT_STORAGE": "personal"
  }
}
```

Copy `.env.example` to `.env` and set `Z2H_EXPLORE_PERSONAL_FOLDER` to your campaign-explore display name (usually `git config user.name`).

**Storage default:** looks and dashboards are saved under `looks/<your name>/` and `dashboards/<your name>/`, then pinned to the matching `index.json`. Pass `shared=true` on create only when you explicitly want `looks/shared/` or `dashboards/shared/`.

Restart Cursor to load the server.

## Team install (one script)

Share **`install-z2h-explore-mcp.sh`** only. Teammates pick any folder.

```bash
# unzip the shared folder, then:
./install-z2h-explore-mcp.sh --dir ~/Desktop/z2h-explore-mcp

# or after you host a git repo:
Z2H_EXPLORE_MCP_REPO='git@...' bash install-z2h-explore-mcp.sh --dir ~/wherever/z2h-explore-mcp
```

Installer does everything: copy/clone repo, venv, `pip install`, write `.env` with your personal folder, merge `~/.cursor/mcp.json` (including `Z2H_EXPLORE_PERSONAL_FOLDER` from `git config user.name`), write `CURSOR_SETUP_PROMPT.md`. Restart Cursor.

### Upgrade existing install (no new folder)

Send teammates **one command** (after one-time clone):

```bash
git clone git@github.com:ram-amit/z2h-explore-mcp.git ~/Development/z2h-explore-mcp
cd ~/Development/z2h-explore-mcp && ./install-z2h-explore-mcp.sh --dir .
```

Already installed? Upgrade config + code:

```bash
cd ~/Development/z2h-explore-mcp && git pull && ./migrate-personal-storage.sh
```

The script: finds install from `~/.cursor/mcp.json`, `git pull` if repo, verifies `api.py` has personal-storage code, writes `.env`, updates `mcp.json` env with their `git config user.name`. Restart Cursor after.

**Slack one-liner to paste:**

> campaign-explore MCP upgrade - run locally, then restart Cursor:
> `cd <your-z2h-explore-mcp-path> && git pull && ./migrate-personal-storage.sh`

### Ship updates to the team

1. **Commit and push** changes to `server.py`, `api.py`, `scripts/install_mcp.py`, and `.env.example` on the shared repo.
2. Teammates **re-run the installer** (or `git pull` + restart Cursor):
   ```bash
   ./install-z2h-explore-mcp.sh --dir ~/path/to/z2h-explore-mcp
   ```
3. Already-installed machines: re-run installer to refresh `~/.cursor/mcp.json` env and `.env`, then restart Cursor.
4. Optional: copy `.cursor/rules/z2h-explore-mcp.mdc` into your team Cursor rules repo so agents default to personal storage in chat too.

| Env / flag | Purpose |
|------------|---------|
| `--dir` / `Z2H_EXPLORE_MCP_DIR` | Install path (default `~/z2h-explore-mcp`) |
| `--repo-url` / `Z2H_EXPLORE_MCP_REPO` | Git clone if files missing |
| `--tarball-url` / `Z2H_EXPLORE_MCP_TARBALL_URL` | Download tarball if files missing |

## Build your own MCP (advanced)

| Asset | Path |
|-------|------|
| Installer | `install-z2h-explore-mcp.sh` |
| Python installer | `scripts/install_mcp.py` |
| Personalized prompt | `scripts/personalize_prompt.py` |

```bash
python3 scripts/personalize_prompt.py --install-dir ~/your/path/z2h-explore-mcp
```

`personalize_prompt.py` detects:

- **Display name** from `git config user.name` (e.g. `Amit Ram`)
- **Account slug** from git email local part (e.g. `amit-ram` from `amit.ram@...`)
- **Development folder** (`~/Development` if it exists)
- **Absolute paths** for `mcp.json` and `z2h-explore-mcp`

Re-run personalize when you switch laptops or change git identity.

Reference implementation: this repo (`server.py`, `api.py`, `schema_loader.py`).

## Tools

| Tool | Purpose |
|------|---------|
| `list_explores` | Campaign Monitoring, Advanced Analytics, LinkedIn Habu |
| `get_dimensions` / `get_measures` / `get_parameters` | Field catalog (CM full; others via sample looks) |
| `get_field_info` | Single field metadata |
| `list_looks` / `get_look` / `create_look` / `update_look` / `delete_look` | Saved views |
| `list_dashboards` / `get_dashboard` / `create_dashboard` / `update_dashboard` / `add_dashboard_tile` / `delete_dashboard` | Dashboards |
| `get_z2h_url` | Build `bigbrain.me/bigbrain-vibe/campaign-explore?...` link |
| `migrate_from_looker` | One-shot Looker → Z2H migration |

## API

Backed by `marketing-foundations`:

- Base: `https://marketing-foundations.bigbrain.me/api/tools/v1/looker-z2h`
- Storage: `GET/PUT/DELETE /storage/file`, `GET /storage/files?prefix=`
- Migration: `POST /migrate/look`, `POST /migrate/dashboard`

**Storage key encoding:** keys returned by `list_*` may contain literal `%20`. Pass those keys as-is to `get_*` / `update_*` / `delete_*`.

## URLs

- Dashboard: `https://bigbrain.me/bigbrain-vibe/campaign-explore?dashboard=9490`
- Look: `https://bigbrain.me/bigbrain-vibe/campaign-explore?look=<uuid>`

## Notes

- Field catalog is pulled from the deployed `mf-campaign-explore` schema chunk (cached in `~/.cache/z2h-explore-mcp/`).
- `run_query` / SQL preview are not in v1; query execution is client-side in campaign-explore.
- Writes use the same unauthenticated storage API as the frontend; if PUT fails, set `BIGBRAIN_AUTH_TOKEN` or connect via VPN.
