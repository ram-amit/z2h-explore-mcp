"""Pre-built MCP specs so teammates do not fill API/tools by hand."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class McpPreset:
    key: str
    label: str
    mcp_name: str
    folder_name: str
    system: str
    api_base_url: str
    api_prefix: str
    auth: str
    goal: str
    tools_markdown: str
    out_of_scope: str
    task_summary: str


Z2H_EXPLORE_INSTALL = McpPreset(
    key="setup",
    label="Install campaign-explore MCP (z2h-explore)",
    mcp_name="z2h-explore",
    folder_name="z2h-explore-mcp",
    system="campaign-explore on bigbrain.me (looks + dashboards)",
    api_base_url="https://marketing-foundations.bigbrain.me",
    api_prefix="/api/tools/v1/looker-z2h",
    auth="Optional: BIGBRAIN_AUTH_TOKEN or BIGBRAIN_SESSION_COOKIE in .env if writes fail off VPN",
    goal="Create and manage Campaign Monitoring looks/dashboards in campaign-explore from Cursor",
    tools_markdown="""\
| Tool | Purpose |
|------|---------|
| `list_explores` | Campaign Monitoring, Advanced Analytics, LinkedIn Habu |
| `get_dimensions` / `get_measures` / `get_parameters` | Field catalog |
| `get_field_info` | Single field metadata |
| `list_looks` / `get_look` / `create_look` / `update_look` / `delete_look` | Saved views |
| `list_dashboards` / `get_dashboard` / `create_dashboard` / `update_dashboard` / `add_dashboard_tile` / `delete_dashboard` | Dashboards |
| `get_z2h_url` | Build campaign-explore URLs |
| `migrate_from_looker` | Migrate a Looker look/dashboard into Z2H |""",
    out_of_scope="""\
- `run_query` / raw SQL execution (not in v1; queries run in the campaign-explore UI)
- Deleting production dashboards without explicit user confirmation
- Posting to Slack or writing monday boards without approval""",
    task_summary="""\
Set up the **existing** z2h-explore MCP at `{{Z2H_EXPLORE_MCP_PATH}}` on this machine. Do not scaffold a new repo.

1. Create venv + `pip install -r requirements.txt` if missing
2. Add the server to `{{MCP_JSON_PATH}}` using absolute paths for **this** user
3. Run a smoke test: `list_explores` and `get_dimensions` with `search=spend`
4. Tell me the exact `mcp.json` block and that I must restart Cursor

When I later ask you to create looks/dashboards:
- Default storage is **personal** (`looks/{{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}/`, `dashboards/{{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}/`), not `looks/shared/` or `dashboards/shared/`
- `create_look` / `create_dashboard` auto-pin to `dashboards/{{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}/index.json` and `looks/{{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}/index.json`
- Use `shared=true` only when I explicitly ask for shared/global storage
- Default date grain: **daily** for "last N days" unless I say weekly/monthly
- Chart x-axis: left-to-right (`xReverseAxis: false`)
- Filter on **cm** table fields when possible; validate empty results and add a text tile or note with alternatives""",
)

PRESETS: dict[str, McpPreset] = {
    Z2H_EXPLORE_INSTALL.key: Z2H_EXPLORE_INSTALL,
}


def get_preset(name: str) -> McpPreset:
    preset = PRESETS.get(name)
    if not preset:
        known = ", ".join(sorted(PRESETS))
        raise ValueError(f"Unknown preset '{name}'. Choose: {known}")
    return preset
