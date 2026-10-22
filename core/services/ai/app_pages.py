"""The app's own screens (single-page-app routes, tabs and dialogs) for the assistant.

The live-structure tool used to list only Django URLs, so every SPA screen (Exchange Rates, Gold Price, Budgets...)
was invisible to the model and it answered "there is no such screen". doc_engine/inventory.json is the documented
navigation map the documentation generator already maintains, so it is the source of truth here. Read-only."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings


def _names(items: Any) -> list[str]:
    return [str(i["name"]).strip() for i in (items or []) if isinstance(i, dict) and str(i.get("name") or "").strip()]


def _tab_entry(tab: dict[str, Any]) -> dict[str, Any]:
    entry: dict[str, Any] = {"name": str(tab.get("name") or "").strip(), "id": str(tab.get("id") or "")}
    actions = _names(tab.get("nested_navigation"))
    if actions:
        entry["actions"] = actions
    return entry


@lru_cache(maxsize=1)
def _catalogue() -> tuple[dict[str, Any], ...]:
    path = Path(settings.BASE_DIR) / "doc_engine" / "inventory.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    pages = []
    for page in data if isinstance(data, list) else []:
        if not isinstance(page, dict) or not page.get("route"):
            continue
        entry: dict[str, Any] = {"route": page["route"], "title": page.get("title") or page["route"],
                                 "open": f"#{page['route']}" if page["route"] != "dashboard" else "/"}
        if page.get("purpose"):
            entry["purpose"] = page["purpose"]
        tabs = [_tab_entry(t) for t in page.get("tabs") or [] if isinstance(t, dict) and t.get("name")]
        if tabs:
            entry["tabs"] = tabs
        actions = _names(page.get("nested_navigation"))
        if actions:
            entry["actions"] = actions
        if page.get("is_admin"):
            entry["admin_only"] = True
        pages.append(entry)
    return tuple(pages)


def app_pages() -> list[dict[str, Any]]:
    """Every documented screen: route, title, how to open it, its tabs and the dialogs/actions inside."""
    return [dict(p) for p in _catalogue()]
