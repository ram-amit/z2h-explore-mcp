# Z2H Explore MCP

**Repo:** https://github.com/ram-amit/z2h-explore-mcp (public)

MCP server for **campaign-explore** looks and dashboards on bigbrain.me. Not Looker (`looker-toolbox` is a different MCP).

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Cursor** or **Claude Desktop** (Mac app) | Not monday browser/workspace Claude |
| **Python 3.10+** | macOS Xcode `python3` is often 3.9 → `brew install python` |
| **git** | For clone-based install |
| **`git config user.name`** | Becomes your campaign-explore personal folder name |

## Install (new users)

**Copy/paste exactly in Terminal:**

```bash
git clone https://github.com/ram-amit/z2h-explore-mcp.git ~/z2h-explore-mcp && cd ~/z2h-explore-mcp && ./install-z2h-explore-mcp.sh --dir .
```

**Claude Code (terminal):**

```bash
./install-z2h-explore-mcp.sh --dir . --clients claude-code
```

Then exit and restart your `claude` session. Run `/mcp` to confirm `z2h-explore` is listed.

**Claude Desktop (Mac app):**

```bash
./install-z2h-explore-mcp.sh --dir . --clients claude-desktop
```

**Both Claude products:**

```bash
./install-z2h-explore-mcp.sh --dir . --clients claude
```

Then follow the **Next steps** printed at the end (restart app, test prompt).

## After install

1. **Quit the app fully** (Cmd+Q), reopen
2. **Cursor:** Settings → MCP → `z2h-explore` connected
3. **New chat**, ask exactly:

```
list explores in campaign-explore
```

Expected: **Campaign Monitoring**, **Advanced Analytics**, **LinkedIn Habu**.

## Verify install

```bash
cd ~/z2h-explore-mcp && ./verify-install.sh
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `invalid option nameipefail` | Don't use `curl \| bash`. Use **git clone** command above. |
| `mcp` pip error / Python 3.9 | `brew install python` then `cd ~/z2h-explore-mcp && rm -rf venv && ./install-z2h-explore-mcp.sh --dir .` |
| `git pull` blocked by local changes | `git reset --hard origin/main && git pull` (installer now auto-resets) |
| MCP not in chat list | Wrong app: use **Cursor**, **Claude Code** (`~/.claude.json`), or **Claude Desktop** — not monday browser Claude |
| Claude Code: MCP missing | Run `--clients claude-code` (not `claude-desktop`). Restart `claude`, check `/mcp` |
| Only see `looker-toolbox` | That's Looker. Ask for **campaign-explore** / **z2h-explore** |
| Install finished but no MCP | Re-run without `--skip-mcp-json`: `./install-z2h-explore-mcp.sh --dir .` |
| Writes fail | Connect VPN or set `BIGBRAIN_AUTH_TOKEN` in `.env` |

## Slack message (team)

> **campaign-explore MCP for Cursor**
>
> paste in **Terminal** (not a Slack link):
> ```
> git clone https://github.com/ram-amit/z2h-explore-mcp.git ~/z2h-explore-mcp && cd ~/z2h-explore-mcp && ./install-z2h-explore-mcp.sh --dir .
> ```
> quit Cursor (Cmd+Q), reopen, test: `list explores in campaign-explore`
>
> stuck? `cd ~/z2h-explore-mcp && ./verify-install.sh` and paste output in thread
>
> repo: https://github.com/ram-amit/z2h-explore-mcp

## Upgrade

```bash
cd ~/z2h-explore-mcp && git pull && ./install-z2h-explore-mcp.sh --dir .
```

Restart Cursor / Claude Desktop after.

## Flags

| Flag | Purpose |
|------|---------|
| `--dir .` | Install path |
| `--clients cursor\|claude-code\|claude-desktop\|claude\|both\|all\|none` | Which app gets MCP config |
| `--python /path/to/python3.12` | Force Python for venv |
| `Z2H_EXPLORE_MCP_DIR` | Override install folder |

## Tools

| Tool | Purpose |
|------|---------|
| `list_explores` | Campaign Monitoring, Advanced Analytics, LinkedIn Habu |
| `get_dimensions` / `get_measures` / `get_parameters` | Field catalog |
| `list_looks` / `create_look` / `update_look` / `delete_look` | Saved views |
| `list_dashboards` / `create_dashboard` / `update_dashboard` | Dashboards |
| `get_z2h_url` | Build campaign-explore URLs |

**Storage default:** personal folder (`looks/<your name>/`, `dashboards/<your name>/`). Pass `shared=true` only when explicitly needed.

## Notes

- Field catalog cached in `~/.cache/z2h-explore-mcp/`
- `run_query` not in v1; queries run in campaign-explore UI
