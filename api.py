"""HTTP client for marketing-foundations looker-z2h API."""

from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any
from urllib.parse import quote

import httpx

DEFAULT_BASE_URL = "https://marketing-foundations.bigbrain.me"
API_PREFIX = "/api/tools/v1/looker-z2h"
LOOKS_SHARED_PREFIX = "looks/shared/"
DASHBOARDS_SHARED_PREFIX = "dashboards/shared/"


def personal_folder_name() -> str | None:
    folder = (os.getenv("Z2H_EXPLORE_PERSONAL_FOLDER") or "").strip()
    return folder or None


def use_shared_storage_by_default() -> bool:
    raw = (os.getenv("Z2H_EXPLORE_DEFAULT_STORAGE") or "personal").strip().lower()
    return raw == "shared"


def looks_prefix(*, shared: bool | None = None, username: str | None = None) -> str:
    if shared is False or (shared is None and not use_shared_storage_by_default()):
        folder = username or personal_folder_name()
        if not folder:
            raise ValueError("Z2H_EXPLORE_PERSONAL_FOLDER is required for personal storage")
        return f"looks/{folder}/"
    return LOOKS_SHARED_PREFIX


def dashboards_prefix(*, shared: bool | None = None, username: str | None = None) -> str:
    if shared is False or (shared is None and not use_shared_storage_by_default()):
        folder = username or personal_folder_name()
        if not folder:
            raise ValueError("Z2H_EXPLORE_PERSONAL_FOLDER is required for personal storage")
        return f"dashboards/{folder}/"
    return DASHBOARDS_SHARED_PREFIX


def encode_storage_key(key: str) -> str:
    """Keys from list API may already contain %20; encodeURIComponent-style quoting is required."""
    return quote(key, safe="")


def sanitize_filename_part(name: str) -> str:
    cleaned = re.sub(r"[^\w\s\-&().]", "", name).strip()
    return cleaned.replace(" ", "%20") or "untitled"


class Z2HExploreClient:
    def __init__(
        self,
        base_url: str | None = None,
        auth_token: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("MARKETING_FOUNDATIONS_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        headers = {"Accept": "application/json"}
        token = auth_token or os.getenv("BIGBRAIN_AUTH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        cookie = os.getenv("BIGBRAIN_SESSION_COOKIE")
        if cookie:
            headers["Cookie"] = cookie
        self._headers = headers

    def _url(self, path: str) -> str:
        return f"{self.base_url}{API_PREFIX}{path}"

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        with httpx.Client(timeout=self.timeout, headers=self._headers) as client:
            response = client.request(method, self._url(path), **kwargs)
            if response.status_code >= 400:
                detail = response.text
                try:
                    payload = response.json()
                    detail = payload.get("description") or payload.get("error") or detail
                except Exception:
                    pass
                raise RuntimeError(f"{method} {path} failed ({response.status_code}): {detail}")
            if response.status_code == 204 or not response.content:
                return None
            return response.json()

    def list_files(self, prefix: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/storage/files?prefix={quote(prefix, safe='')}")

    def get_file(self, key: str) -> dict[str, Any]:
        encoded = encode_storage_key(key)
        payload = self._request("GET", f"/storage/file?key={encoded}")
        content = payload.get("content")
        if isinstance(content, str):
            return json.loads(content)
        return payload

    def put_file(self, key: str, content: dict[str, Any]) -> None:
        body = {"key": key, "content": json.dumps(content)}
        self._request("PUT", "/storage/file", json=body)

    def delete_file(self, key: str) -> None:
        encoded = encode_storage_key(key)
        self._request("DELETE", f"/storage/file?key={encoded}")

    def migrate_look(self, looker_url: str, *, dry_run: bool = False, force: bool = True) -> Any:
        return self._request(
            "POST",
            "/migrate/look",
            json={"lookerUrl": looker_url, "dryRun": dry_run, "force": force},
        )

    def migrate_dashboard(self, dashboard_url: str, *, dry_run: bool = False, force: bool = True) -> Any:
        return self._request(
            "POST",
            "/migrate/dashboard",
            json={"dashboardUrl": dashboard_url, "dryRun": dry_run, "force": force},
        )

    @staticmethod
    def parse_storage_entry(key: str) -> dict[str, str]:
        filename = key.rsplit("/", 1)[-1].removesuffix(".json")
        if "__" in filename:
            entry_id, name = filename.split("__", 1)
        else:
            entry_id, name = filename, filename
        return {
            "key": key,
            "id": entry_id,
            "name": name.replace("%20", " "),
        }

    def list_looks(
        self,
        *,
        prefix: str = LOOKS_SHARED_PREFIX,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        entries = [self.parse_storage_entry(item["key"]) for item in self.list_files(prefix)]
        if search:
            needle = search.lower()
            entries = [e for e in entries if needle in e["name"].lower() or needle in e["id"].lower()]
        total = len(entries)
        page = entries[offset : offset + limit]
        return {"total": total, "offset": offset, "limit": limit, "looks": page}

    def list_dashboards(
        self,
        *,
        prefix: str = DASHBOARDS_SHARED_PREFIX,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        entries = [self.parse_storage_entry(item["key"]) for item in self.list_files(prefix)]
        if search:
            needle = search.lower()
            entries = [e for e in entries if needle in e["name"].lower() or needle in e["id"].lower()]
        total = len(entries)
        page = entries[offset : offset + limit]
        return {"total": total, "offset": offset, "limit": limit, "dashboards": page}

    def _look_search_prefixes(self) -> list[str]:
        prefixes = []
        folder = personal_folder_name()
        if folder:
            prefixes.append(f"looks/{folder}/")
        prefixes.append(LOOKS_SHARED_PREFIX)
        return prefixes

    def _dashboard_search_prefixes(self) -> list[str]:
        prefixes = []
        folder = personal_folder_name()
        if folder:
            prefixes.append(f"dashboards/{folder}/")
        prefixes.append(DASHBOARDS_SHARED_PREFIX)
        return prefixes

    def resolve_look_key(self, key_or_id: str, name: str | None = None) -> str:
        if key_or_id.startswith("looks/"):
            return key_or_id
        if name:
            safe_name = sanitize_filename_part(name)
            try:
                return f"{looks_prefix()}{key_or_id}__{safe_name}.json"
            except ValueError:
                return f"{LOOKS_SHARED_PREFIX}{key_or_id}__{safe_name}.json"
        for prefix in self._look_search_prefixes():
            for item in self.list_files(prefix):
                parsed = self.parse_storage_entry(item["key"])
                if parsed["id"] == key_or_id:
                    return item["key"]
        raise ValueError(f"Look not found for id: {key_or_id}")

    def resolve_dashboard_key(self, key_or_id: str, name: str | None = None) -> str:
        if key_or_id.startswith("dashboards/"):
            return key_or_id
        if name:
            safe_name = sanitize_filename_part(name)
            try:
                return f"{dashboards_prefix()}{key_or_id}__{safe_name}.json"
            except ValueError:
                return f"{DASHBOARDS_SHARED_PREFIX}{key_or_id}__{safe_name}.json"
        for prefix in self._dashboard_search_prefixes():
            for item in self.list_files(prefix):
                parsed = self.parse_storage_entry(item["key"])
                if parsed["id"] == key_or_id:
                    return item["key"]
        raise ValueError(f"Dashboard not found for id: {key_or_id}")

    def build_look_key(self, look_id: str, name: str, *, shared: bool = True, username: str | None = None) -> str:
        safe_name = sanitize_filename_part(name)
        if shared:
            return f"{LOOKS_SHARED_PREFIX}{look_id}__{safe_name}.json"
        if not username:
            raise ValueError("username is required for non-shared looks")
        return f"looks/{username}/{look_id}__{safe_name}.json"

    def build_dashboard_key(
        self,
        dashboard_id: str,
        name: str,
        *,
        shared: bool = True,
        username: str | None = None,
    ) -> str:
        safe_name = sanitize_filename_part(name)
        if shared:
            return f"{DASHBOARDS_SHARED_PREFIX}{dashboard_id}__{safe_name}.json"
        if not username:
            raise ValueError("username is required for non-shared dashboards")
        return f"dashboards/{username}/{dashboard_id}__{safe_name}.json"

    def new_look_id(self) -> str:
        return str(uuid.uuid4())

    def pin_look_to_index(self, look_id: str, name: str) -> str:
        folder = personal_folder_name()
        if not folder:
            raise ValueError("Z2H_EXPLORE_PERSONAL_FOLDER is required to pin looks")
        index_key = f"looks/{folder}/index.json"
        index = self._read_index(index_key)
        items = [item for item in index.get("items", []) if item.get("id") != look_id]
        items.insert(0, {"id": look_id, "name": name, "subfolder": None})
        index["items"] = items
        self.put_file(index_key, index)
        return index_key

    def pin_dashboard_to_index(self, dashboard_id: str, name: str) -> str:
        folder = personal_folder_name()
        if not folder:
            raise ValueError("Z2H_EXPLORE_PERSONAL_FOLDER is required to pin dashboards")
        index_key = f"dashboards/{folder}/index.json"
        index = self._read_index(index_key)
        items = [item for item in index.get("items", []) if item.get("id") != dashboard_id]
        items.insert(0, {"id": dashboard_id, "name": name, "subfolder": None})
        index["items"] = items
        self.put_file(index_key, index)
        return index_key

    def _read_index(self, index_key: str) -> dict[str, Any]:
        try:
            return self.get_file(index_key)
        except RuntimeError:
            return {"version": 1, "items": []}
