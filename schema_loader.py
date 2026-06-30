"""Load campaign-explore field catalog from the deployed Z2H build."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

from explores import EXPLORES

MF_ASSETS_URL = "https://bigbrain-zth-mf-assets.bigbrain.me/mf-assets"
MF_BUILD_BASE = "https://bigbrain-zth-mf-assets.bigbrain.me/mf-campaign-explore"
CACHE_DIR = Path.home() / ".cache" / "z2h-explore-mcp"
CACHE_FILE = CACHE_DIR / "schema.json"
BUNDLED_SCHEMA = Path(__file__).parent / "data" / "schema.json"


class SchemaLoader:
    def __init__(self, build_version: str | None = None, cache_ttl_hours: int = 24) -> None:
        self.build_version = build_version
        self.cache_ttl_hours = cache_ttl_hours
        self._schema: dict[str, Any] | None = None

    def get_schema(self) -> dict[str, Any]:
        if self._schema is not None:
            return self._schema
        self._schema = self._load_schema()
        return self._schema

    def _load_schema(self) -> dict[str, Any]:
        if CACHE_FILE.exists() and not self._cache_is_stale():
            return json.loads(CACHE_FILE.read_text())

        try:
            schema = self._fetch_schema_from_build()
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(json.dumps(schema))
            return schema
        except Exception:
            if BUNDLED_SCHEMA.exists():
                return json.loads(BUNDLED_SCHEMA.read_text())
            raise

    def _cache_is_stale(self) -> bool:
        if self.build_version:
            return True
        age_hours = (time.time() - CACHE_FILE.stat().st_mtime) / 3600
        return age_hours > self.cache_ttl_hours

    def _resolve_build_version(self, client: httpx.Client) -> str:
        if self.build_version:
            return self.build_version
        manifest = client.get(MF_ASSETS_URL, timeout=30).json()
        version = manifest.get("mf-campaign-explore", {}).get("version")
        if not version:
            raise RuntimeError("Could not resolve mf-campaign-explore build version from mf-assets")
        return str(version)

    def _fetch_schema_from_build(self) -> dict[str, Any]:
        with httpx.Client(timeout=60) as client:
            version = self._resolve_build_version(client)
            main_js_url = f"{MF_BUILD_BASE}/{version}/static/js/main.js"
            main_resp = client.get(main_js_url)
            if main_resp.status_code == 404:
                # fallback: index may reference a hashed main chunk
                index = client.get(f"{MF_BUILD_BASE}/{version}/index.html").text
                match = re.search(r"static/js/[^\"']+main[^\"']+\.js", index)
                if not match:
                    raise RuntimeError(f"Could not find main JS bundle for build {version}")
                main_js_url = f"{MF_BUILD_BASE}/{version}/{match.group(0)}"
                main_resp = client.get(main_js_url)
            main_resp.raise_for_status()

            chunk_match = re.search(r"static/js/schema\.[A-Za-z0-9_-]+\.chunk\.js", main_resp.text)
            if not chunk_match:
                raise RuntimeError("Could not find schema chunk in campaign-explore bundle")
            chunk_url = f"{MF_BUILD_BASE}/{version}/{chunk_match.group(0)}"
            chunk_text = client.get(chunk_url).raise_for_status().text

        json_match = re.match(r"const n='(.*)';export", chunk_text, re.DOTALL)
        if not json_match:
            raise RuntimeError("Unexpected schema chunk format")
        raw = json_match.group(1).encode().decode("unicode_escape")
        return json.loads(raw)

    def fields_for_explore(
        self,
        explore_name: str,
        *,
        role: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        explore = EXPLORES.get(explore_name)
        if not explore:
            raise ValueError(f"Unknown explore: {explore_name}")

        schema = self.get_schema()
        columns: list[dict[str, Any]] = schema.get("columns", [])
        allowed_views = set(explore.schema_views)
        results: list[dict[str, Any]] = []

        for col in columns:
            if allowed_views and col.get("view") not in allowed_views:
                continue
            if role and col.get("role") != role:
                continue
            if search:
                needle = search.lower()
                haystack = " ".join(
                    str(col.get(k, "")) for k in ("name", "displayName", "description", "category")
                ).lower()
                if needle not in haystack:
                    continue
            results.append(
                {
                    "name": col.get("name"),
                    "display_name": col.get("displayName"),
                    "role": col.get("role"),
                    "category": col.get("category"),
                    "data_type": col.get("dataType"),
                    "view": col.get("view"),
                    "description": col.get("description", ""),
                    "hidden": col.get("hidden", False),
                }
            )

        return results[offset : offset + limit]

    def field_info(self, field_name: str, explore_name: str | None = None) -> dict[str, Any] | None:
        schema = self.get_schema()
        columns: list[dict[str, Any]] = schema.get("columns", [])
        target = field_name.upper()
        allowed_views: set[str] | None = None
        if explore_name:
            explore = EXPLORES.get(explore_name)
            if explore and explore.schema_views:
                allowed_views = set(explore.schema_views)

        for col in columns:
            if col.get("name", "").upper() != target:
                continue
            if allowed_views and col.get("view") not in allowed_views:
                continue
            return col
        return None
