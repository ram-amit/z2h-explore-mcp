# Paste this into Cursor or Claude Code to build your MCP

Generated for **{{DISPLAY_NAME}}** on this machine. Re-run `python3 scripts/personalize_prompt.py` if you switch laptops or git identity.

Copy everything below the line into a new chat. Fill in only the fields still marked `YOUR_*`.

---

## Task

Build a local **MCP server** (Model Context Protocol) so I can use it from Cursor or Claude Code.

Use the existing reference implementation at `{{Z2H_EXPLORE_MCP_PATH}}` as the pattern. Read these files before writing code:

- `server.py` (FastMCP tools)
- `api.py` (HTTP client to the backing API)
- `README.md` (setup + `mcp.json` registration)
- `explores.py` / `schema_loader.py` (only if my MCP needs field discovery)

Do not copy the Z2H explore logic unless my MCP is also for campaign-explore. Use the same **project structure and conventions**.

---

## My machine (auto-detected)

| Field | Value |
|-------|--------|
| **Display name** | {{DISPLAY_NAME}} |
| **Account slug** (SSO / short id) | `{{ACCOUNT_SLUG}}` |
| **System username** | `{{SYSTEM_USERNAME}}` |
| **Home** | `{{HOME}}` |
| **Development folder** | `{{DEVELOPMENT_ROOT}}` |
| **Reference MCP** | `{{Z2H_EXPLORE_MCP_PATH}}` |
| **Cursor MCP config** | `{{MCP_JSON_PATH}}` |
| **campaign-explore personal folder** | `{{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}` (pin dashboards/looks in `dashboards/{{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}/index.json`) |

---

## My MCP spec

| Field | Value |
|-------|--------|
| **MCP name** (kebab-case, used in `mcp.json`) | `YOUR_MCP_NAME` |
| **Folder** | `{{DEVELOPMENT_ROOT}}/YOUR_MCP_FOLDER` |
| **What it connects to** | `YOUR_SYSTEM` (e.g. internal API, Snowflake, monday board, Google Ads) |
| **Base URL / entrypoint** | `YOUR_API_BASE_URL` |
| **Auth** | `YOUR_AUTH` (e.g. env var token, session cookie, OAuth, none on VPN) |
| **Primary user goal** | `YOUR_GOAL` (one sentence: what should teammates ask the agent to do?) |

### Tools I need (list 3-8)

1. `YOUR_TOOL_1` - ...
2. `YOUR_TOOL_2` - ...
3. `YOUR_TOOL_3` - ...

### Out of scope for v1

- `YOUR_OUT_OF_SCOPE` (e.g. run_query, delete prod data, write to Slack without approval)

---

## Requirements

### 1. Stack

- **Python 3.11+** with `mcp[cli]`, `httpx`, `python-dotenv`
- **FastMCP** (`from mcp.server.fastmcp import FastMCP`)
- Entry point: `server.py` runnable as `python server.py`

### 2. Layout

```
YOUR_MCP_FOLDER/
├── server.py          # MCP tools only; thin layer
├── api.py             # HTTP / SDK client; no MCP imports
├── requirements.txt
├── .env.example
├── README.md          # setup for teammates
└── data/              # optional bundled schemas, samples
```

### 3. Tool design rules

- Every tool returns **JSON strings** (`json.dumps(..., indent=2)`), not raw dicts
- Tool docstrings are what the agent reads: include parameter formats and examples
- **Discover before mutate**: if there is a catalog (fields, boards, accounts), expose `list_*` / `get_*` before `create_*` / `update_*`
- Validate inputs early; return clear errors (`Unknown explore 'x'. Use list_explores.`)
- Prefer **read existing objects** and copy their JSON shape before inventing payloads (see `get_look` in z2h-explore-mcp)

### 4. Auth and secrets

- Read secrets from `.env` only; never hardcode tokens
- Document every env var in `.env.example`
- README must say: do not commit `.env`

### 5. Cursor registration

After the server works, print the exact block to add to `{{MCP_JSON_PATH}}`:

```json
"YOUR_MCP_NAME": {
  "command": "{{DEVELOPMENT_ROOT}}/YOUR_MCP_FOLDER/venv/bin/python3",
  "args": ["{{DEVELOPMENT_ROOT}}/YOUR_MCP_FOLDER/server.py"],
  "cwd": "{{DEVELOPMENT_ROOT}}/YOUR_MCP_FOLDER"
}
```

Use these absolute paths for **this** machine. Tell me to restart Cursor.

### 6. README for teammates

Include:

- One-line what it does
- `venv` + `pip install` steps
- `mcp.json` snippet with **my** absolute paths above
- Table of tools with when to use each
- Example agent prompts (2-3)
- Known limitations and pitfalls

### 7. Test plan (run before handing off)

1. `python -c "from api import ..."` smoke import
2. Start server locally (or call tools via a one-off script)
3. One read tool against real API
4. One write tool (if applicable) with a test object named `[TEST] ...`
5. Confirm tool appears in Cursor MCP list after restart

---

## Pitfalls learned from z2h-explore-mcp (apply if relevant)

| Pitfall | Fix |
|---------|-----|
| Saved to **shared** storage, user does not see it in personal account | Personal view is an **index.json** bookmark under `dashboards/{{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}/` or `looks/{{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}/`; pin items there after create |
| Filter on joined table breaks queries | Filter on the **main table** fields when possible; validate in Snowflake before shipping |
| `LIKE` with `%wildcards%` | campaign-explore adds wildcards; pass plain `keyword` |
| "Last 90 days" interpreted as weekly | Default to **daily** (`CREATED_AT_DATE`, `dateTrunc: day`) unless user asks for weekly/monthly |
| Chart dates right-to-left | Set `xReverseAxis: false` |
| Empty results | Flag in a **text tile** or return a note with alternative filters / queries |

---

## Deliverables

1. Full working MCP folder under `{{DEVELOPMENT_ROOT}}/YOUR_MCP_FOLDER`
2. `README.md` with **my** absolute paths (not `~/...` placeholders)
3. Copy-paste `mcp.json` block for `{{MCP_JSON_PATH}}`
4. 2-3 example prompts I can try in Cursor immediately after restart

Build it end-to-end. Do not leave TODOs or placeholders in code except `YOUR_MCP_NAME`, `YOUR_MCP_FOLDER`, and the spec fields I still need to fill.

---

## Optional: campaign-explore MCP

If my MCP is for **campaign-explore** (looks/dashboards on bigbrain.me), do not start from scratch. Clone and extend `{{Z2H_EXPLORE_MCP_PATH}}` instead of generating a new server.

When creating dashboards/looks for **{{DISPLAY_NAME}}**, pin them to:

- `dashboards/{{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}/index.json`
- `looks/{{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}/index.json`

Reference URLs:

- App: `https://bigbrain.me/bigbrain-vibe/campaign-explore`
- API: `https://marketing-foundations.bigbrain.me/api/tools/v1/looker-z2h`
- Gold-standard look for daily charts: look id `122809` (Partnerstack Daily)
- Text dashboard tiles: `kind: "text"` with `title`, `body`, optional `subtitle`
