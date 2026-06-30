"""
Z2H Explore MCP Server

Create and manage looks (saved views) and dashboards in campaign-explore on bigbrain.me.
Replaces Looker MCP for Z2H marketing analytics workflows.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from api import (
    Z2HExploreClient,
    dashboards_prefix,
    looks_prefix,
    personal_folder_name,
    use_shared_storage_by_default,
)
from explores import EXPLORE_PARAMETERS, EXPLORES, Z2H_APP_BASE
from schema_loader import SchemaLoader

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

mcp = FastMCP(
    "z2h-explore",
    instructions=(
        "Z2H Explore MCP for monday.com marketing analytics (campaign-explore). "
        "Use list_explores to see available explores (Campaign Monitoring, Advanced Analytics, LinkedIn Habu). "
        "Use get_dimensions/get_measures/get_parameters for field discovery on campaign_monitoring. "
        "Use list_looks/list_dashboards then get_look/get_dashboard to inspect saved content. "
        "Use create_look/create_dashboard to save new views; opens at https://bigbrain.me/bigbrain-vibe/campaign-explore. "
        "Default storage is the user's personal folder (Z2H_EXPLORE_PERSONAL_FOLDER), not looks/shared or dashboards/shared. "
        "After create_look/create_dashboard, items are pinned to looks/<folder>/index.json and dashboards/<folder>/index.json. "
        "Only pass shared=true when the user explicitly asks for shared/global storage. "
        "Dashboard URLs use ?dashboard=<looker_id>. Looks open by look id in the app sidebar. "
        "For keys with spaces, always use the exact key returned by list_* APIs when calling get/update/delete."
    ),
)

_client: Z2HExploreClient | None = None
_schema: SchemaLoader | None = None


def client() -> Z2HExploreClient:
    global _client
    if _client is None:
        _client = Z2HExploreClient()
    return _client


def schema() -> SchemaLoader:
    global _schema
    if _schema is None:
        _schema = SchemaLoader(build_version=os.getenv("CAMPAIGN_EXPLORE_BUILD_VERSION"))
    return _schema


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def _explore_ref(explore_name: str):
    ref = EXPLORES.get(explore_name)
    if not ref:
        raise ValueError(f"Unknown explore '{explore_name}'. Use list_explores.")
    return ref


@mcp.tool()
def list_explores() -> str:
    """List Z2H explores available in campaign-explore."""
    items = []
    for name, ref in EXPLORES.items():
        items.append(
            {
                "explore_name": name,
                "label": ref.label,
                "lkml_path": ref.lkml_path,
                "model_path": ref.model_path,
                "date_column": ref.date_column,
                "field_catalog": "full" if ref.schema_views else "use Looker or sample looks",
            }
        )
    return _json(items)


@mcp.tool()
def get_parameters(explore_name: str = "campaign_monitoring") -> str:
    """Get explore parameters (locks, attribution model, granularity, etc.)."""
    _explore_ref(explore_name)
    params = EXPLORE_PARAMETERS.get(explore_name, [])
    if explore_name == "campaign_monitoring":
        schema_params = schema().fields_for_explore(explore_name, role="parameter", limit=50)
        if schema_params:
            return _json({"explore": explore_name, "parameters": schema_params})
    return _json({"explore": explore_name, "parameters": params})


@mcp.tool()
def get_dimensions(
    explore_name: str = "campaign_monitoring",
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """List dimensions for an explore. Full catalog for campaign_monitoring only."""
    _explore_ref(explore_name)
    fields = schema().fields_for_explore(explore_name, role="dimension", search=search, limit=limit, offset=offset)
    return _json({"explore": explore_name, "count": len(fields), "dimensions": fields})


@mcp.tool()
def get_measures(
    explore_name: str = "campaign_monitoring",
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """List measures for an explore. Full catalog for campaign_monitoring only."""
    _explore_ref(explore_name)
    fields = schema().fields_for_explore(explore_name, role="measure", search=search, limit=limit, offset=offset)
    return _json({"explore": explore_name, "count": len(fields), "measures": fields})


@mcp.tool()
def get_field_info(field_name: str, explore_name: str | None = "campaign_monitoring") -> str:
    """Get metadata for a single field (dimension, measure, or parameter)."""
    info = schema().field_info(field_name, explore_name)
    if not info:
        return _json({"error": f"Field '{field_name}' not found", "explore": explore_name})
    return _json(info)


def _resolve_shared_flag(shared: bool | None) -> bool:
    if shared is None:
        return use_shared_storage_by_default()
    return shared


def _storage_meta(*, shared: bool) -> dict[str, Any]:
    folder = personal_folder_name()
    return {
        "storage": "shared" if shared else "personal",
        "personal_folder": folder,
    }


@mcp.tool()
def list_looks(
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    prefix: str | None = None,
    shared: bool | None = None,
) -> str:
    """List saved looks in Z2H storage. Defaults to the configured personal folder."""
    resolved_prefix = prefix or looks_prefix(shared=shared)
    return _json(client().list_looks(prefix=resolved_prefix, search=search, limit=limit, offset=offset))


@mcp.tool()
def get_look(key_or_id: str, name: str | None = None) -> str:
    """Get a look JSON by storage key or id (optionally with name for disambiguation)."""
    key = client().resolve_look_key(key_or_id, name=name)
    look = client().get_file(key)
    return _json({"key": key, "look": look})


@mcp.tool()
def create_look(
    name: str,
    explore_name: str = "campaign_monitoring",
    dimensions: list[str] | None = None,
    measures: list[dict[str, str]] | None = None,
    filters: list[dict[str, Any]] | None = None,
    date_column: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    date_trunc: str = "week",
    row_limit: int = 500,
    chart_type: str = "table",
    sharable: bool = True,
    look_id: str | None = None,
    look_json: str | None = None,
    shared: bool | None = None,
) -> str:
    """
    Create a new look in Z2H storage (personal folder by default).

    measures format: [{"name": "SPEND", "agg": "SUM"}, ...]
    Or pass full look_json to override generated structure.
    Pass shared=true only when the user explicitly wants global/shared storage.
    """
    ref = _explore_ref(explore_name)
    look_uuid = look_id or client().new_look_id()
    is_shared = _resolve_shared_flag(shared)
    username = personal_folder_name()

    if look_json:
        payload = json.loads(look_json)
    else:
        selected_dims = dimensions or ["DYNAMIC_PERIOD"]
        selected_measures = measures or [{"name": "SPEND", "agg": "SUM"}]
        payload = {
            "schemaVersion": 1,
            "id": look_uuid,
            "name": name,
            "sharable": sharable,
            "explore": {
                "lkmlPath": ref.lkml_path,
                "modelPath": ref.model_path,
                "exploreName": ref.explore_name,
            },
            "query": {
                "selectedDims": selected_dims,
                "selectedMeasures": selected_measures,
                "filters": filters or [],
                "dateFilters": [],
                "dateStart": date_start,
                "dateEnd": date_end,
                "dateTrunc": date_trunc,
                "dateColumn": date_column or ref.date_column,
                "rowLimit": row_limit,
            },
            "chartConfig": {
                "type": chart_type,
                "dimension": selected_dims[0] if selected_dims else None,
                "metrics": [m["name"] for m in selected_measures],
            },
        }

    key = client().build_look_key(
        payload.get("id", look_uuid),
        name,
        shared=is_shared,
        username=username,
    )
    client().put_file(key, payload)
    pinned_to = None
    if not is_shared and username:
        pinned_to = client().pin_look_to_index(payload.get("id", look_uuid), name)
    return _json(
        {
            "key": key,
            "id": payload.get("id", look_uuid),
            "name": name,
            "url": f"{Z2H_APP_BASE}?look={payload.get('id', look_uuid)}",
            "look": payload,
            "pinned_to": pinned_to,
            **_storage_meta(shared=is_shared),
        }
    )


@mcp.tool()
def update_look(key: str, look_json: str) -> str:
    """Replace an existing look JSON at the given storage key."""
    payload = json.loads(look_json)
    client().put_file(key, payload)
    return _json({"key": key, "updated": True, "id": payload.get("id")})


@mcp.tool()
def delete_look(key: str) -> str:
    """Delete a look by storage key."""
    client().delete_file(key)
    return _json({"key": key, "deleted": True})


@mcp.tool()
def list_dashboards(
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    prefix: str | None = None,
    shared: bool | None = None,
) -> str:
    """List dashboards in Z2H storage. Defaults to the configured personal folder."""
    resolved_prefix = prefix or dashboards_prefix(shared=shared)
    return _json(client().list_dashboards(prefix=resolved_prefix, search=search, limit=limit, offset=offset))


@mcp.tool()
def get_dashboard(key_or_id: str, name: str | None = None) -> str:
    """Get a dashboard JSON by storage key or Looker dashboard id."""
    key = client().resolve_dashboard_key(key_or_id, name=name)
    dashboard = client().get_file(key)
    return _json(
        {
            "key": key,
            "dashboard": dashboard,
            "url": f"{Z2H_APP_BASE}?dashboard={dashboard.get('id', key_or_id)}",
        }
    )


@mcp.tool()
def create_dashboard(
    name: str,
    dashboard_id: str | None = None,
    tiles: list[dict[str, Any]] | None = None,
    filters: list[dict[str, Any]] | None = None,
    sharable: bool = True,
    dashboard_json: str | None = None,
    shared: bool | None = None,
) -> str:
    """
    Create a dashboard in Z2H storage (personal folder by default).

    tiles format:
    [{"kind": "visualization", "lookId": "<look-id>", "title": "...", "layout": {"x":0,"y":0,"w":6,"h":5}}]
    Or pass dashboard_json for full control.
    Pass shared=true only when the user explicitly wants global/shared storage.
    """
    dash_id = dashboard_id or str(uuid.uuid4())
    is_shared = _resolve_shared_flag(shared)
    username = personal_folder_name()

    if dashboard_json:
        payload = json.loads(dashboard_json)
    else:
        payload = {
            "schemaVersion": 1,
            "id": dash_id,
            "name": name,
            "sharable": sharable,
            "tiles": tiles or [],
            "filters": filters or [],
        }

    key = client().build_dashboard_key(
        str(payload.get("id", dash_id)),
        name,
        shared=is_shared,
        username=username,
    )
    client().put_file(key, payload)
    pinned_to = None
    if not is_shared and username:
        pinned_to = client().pin_dashboard_to_index(str(payload.get("id", dash_id)), name)
    return _json(
        {
            "key": key,
            "id": payload.get("id", dash_id),
            "name": name,
            "url": f"{Z2H_APP_BASE}?dashboard={payload.get('id', dash_id)}",
            "dashboard": payload,
            "pinned_to": pinned_to,
            **_storage_meta(shared=is_shared),
        }
    )


@mcp.tool()
def update_dashboard(key: str, dashboard_json: str) -> str:
    """Replace an existing dashboard JSON at the given storage key."""
    payload = json.loads(dashboard_json)
    client().put_file(key, payload)
    return _json({"key": key, "updated": True, "id": payload.get("id")})


@mcp.tool()
def add_dashboard_tile(
    key_or_id: str,
    look_id: str,
    title: str,
    x: int = 0,
    y: int = 0,
    w: int = 6,
    h: int = 5,
    name: str | None = None,
) -> str:
    """Add a visualization tile referencing an existing look to a dashboard."""
    key = client().resolve_dashboard_key(key_or_id, name=name)
    dashboard = client().get_file(key)
    tile_id = look_id
    tile = {
        "kind": "visualization",
        "id": tile_id,
        "lookId": look_id,
        "title": title,
        "layout": {"x": x, "y": y, "w": w, "h": h},
    }
    tiles = dashboard.get("tiles", [])
    tiles.append(tile)
    dashboard["tiles"] = tiles
    client().put_file(key, dashboard)
    return _json({"key": key, "dashboard_id": dashboard.get("id"), "added_tile": tile, "tile_count": len(tiles)})


@mcp.tool()
def delete_dashboard(key: str) -> str:
    """Delete a dashboard by storage key."""
    client().delete_file(key)
    return _json({"key": key, "deleted": True})


@mcp.tool()
def get_z2h_url(kind: str, id: str) -> str:
    """Build campaign-explore URL for a look or dashboard. kind: 'look' | 'dashboard'."""
    if kind not in {"look", "dashboard"}:
        raise ValueError("kind must be 'look' or 'dashboard'")
    param = "dashboard" if kind == "dashboard" else "look"
    return _json({"url": f"{Z2H_APP_BASE}?{param}={id}"})


@mcp.tool()
def migrate_from_looker(url: str, kind: str = "dashboard", dry_run: bool = False) -> str:
    """
    Migrate a Looker look or dashboard into Z2H via marketing-foundations.

    kind: 'look' | 'dashboard'
    url: full Looker URL (e.g. https://looker.bigbrain.me:19999/dashboards/9490)
    """
    if kind == "dashboard":
        result = client().migrate_dashboard(url, dry_run=dry_run)
    elif kind == "look":
        result = client().migrate_look(url, dry_run=dry_run)
    else:
        raise ValueError("kind must be 'look' or 'dashboard'")
    return _json(result)


if __name__ == "__main__":
    mcp.run()
