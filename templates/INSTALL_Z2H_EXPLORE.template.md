# Set up my campaign-explore MCP in Cursor

Generated for **{{DISPLAY_NAME}}**. Everything below is pre-filled. Copy from the line below into a **new Cursor chat** and send. Do not edit unless something fails.

---

## Task

{{TASK_SUMMARY}}

Read the reference code at `{{Z2H_EXPLORE_MCP_PATH}}` (`server.py`, `api.py`, `README.md`) before changing anything.

---

## My machine (auto-detected)

| Field | Value |
|-------|--------|
| **Display name** | {{DISPLAY_NAME}} |
| **Account slug** | `{{ACCOUNT_SLUG}}` |
| **Home** | `{{HOME}}` |
| **MCP folder** | `{{MCP_FOLDER}}` |
| **Cursor config** | `{{MCP_JSON_PATH}}` |
| **campaign-explore personal folder** | `{{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}` |

---

## MCP spec (pre-filled)

| Field | Value |
|-------|--------|
| **MCP name** | `{{MCP_NAME}}` |
| **Connects to** | {{SYSTEM}} |
| **API base** | `{{API_BASE_URL}}{{API_PREFIX}}` |
| **Auth** | {{AUTH}} |
| **Goal** | {{GOAL}} |

### Tools (already defined in this MCP)

{{TOOLS_MARKDOWN}}

### Out of scope

{{OUT_OF_SCOPE}}

---

## Cursor registration

Use this exact block in `{{MCP_JSON_PATH}}`:

```json
"{{MCP_NAME}}": {
  "command": "{{MCP_FOLDER}}/venv/bin/python3",
  "args": ["{{MCP_FOLDER}}/server.py"],
  "cwd": "{{MCP_FOLDER}}",
  "env": {
    "Z2H_EXPLORE_PERSONAL_FOLDER": "{{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}",
    "Z2H_EXPLORE_DEFAULT_STORAGE": "personal"
  }
}
```

The installer also writes `{{MCP_FOLDER}}/.env` with the same values.

---

## Pitfalls (campaign-explore)

| Issue | Fix |
|-------|-----|
| Dashboard saved to shared instead of personal | Re-run installer or set `Z2H_EXPLORE_DEFAULT_STORAGE=personal` and `Z2H_EXPLORE_PERSONAL_FOLDER={{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}` in `mcp.json` env + `.env` |
| Dashboard not in personal sidebar | `create_*` should auto-pin; if missing, add id to `dashboards/{{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}/index.json` |
| `UTM_*` filters break visits | Use `CAMPAIGN` on cm table; `LIKE` value without `%` (e.g. `agentic`) |
| "Last 90 days" shown weekly | Use `CREATED_AT_DATE` + `dateTrunc: day` |
| Chart dates reversed | `xReverseAxis: false` |
| Empty signups | Add `kind: "text"` tile explaining why + suggest `PRODUCT_DTR` or Snowflake |

---

## Deliverables

1. Working venv + dependencies in `{{MCP_FOLDER}}`
2. Updated `{{MCP_JSON_PATH}}` snippet for me to paste
3. Confirmation that `list_explores` works
4. Three example prompts I can try after restarting Cursor

Execute now. No clarifying questions unless a command fails.
