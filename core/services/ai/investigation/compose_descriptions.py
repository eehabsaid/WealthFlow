"""The documented text of each screen, tab and dialog, looked up by key (not searched).

doc_engine/content/page_descriptions.json holds one entry per page ("route"), tab ("route::tab-id") and dialog
("route::tab-id::dialog_name" or "route::dialog_name"). The guide used to receive them only through a ranked text search,
which for a screen with five tabs returned some of the tabs and left the model to say "nothing is defined for this tab" about
the others. A key lookup returns every entry of the unit, so nothing the app documents is left out and nothing has to be guessed."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from django.conf import settings

PLACEHOLDER = "Configure the administrative settings and preferences for "
MAX_CHARS = 3000          # one entry; the longest real one is about 3,500 characters
ALIASES = {"employment": ("salary-7",)}    # the Employment screen documents its dialogs under the salary page's key


@lru_cache(maxsize=1)
def _all() -> dict:
    path = Path(settings.BASE_DIR) / "doc_engine" / "content" / "page_descriptions.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, dict) and v.get("purpose") and not str(v["purpose"]).startswith(PLACEHOLDER)}


def slug(name: str) -> str:
    return re.sub(r"\W+", "_", str(name).lower()).strip("_")


def _entry(key: str) -> dict | None:
    item = _all().get(key)
    if not item:
        return None
    text = {"purpose": str(item["purpose"]), "steps": [str(s) for s in item.get("steps") or []]}
    while len(json.dumps(text, ensure_ascii=False)) > MAX_CHARS and len(text["steps"]) > 1:
        text["steps"].pop()
    return text


def _children(prefix: str) -> list[dict]:
    """Every dialog / section documented directly under `prefix` ("route::tab::"), in file order."""
    out = []
    for key in _all():
        if key.startswith(prefix) and "::" not in key[len(prefix):]:
            tail = key[len(prefix):]
            out.append({"name": tail.replace("_", " ").replace("-", " ").strip().title(), "_key": tail, **(_entry(key) or {})})
    return out


def page_evidence(route: str, tab_ids: list[str]) -> dict:
    """{"description", "items": [...]} for the page itself and, per tab id, {"description", "items"}."""
    tabs = {tid: {"description": _entry(f"{route}::{tid}"), "items": _children(f"{route}::{tid}::")} for tid in tab_ids}
    page_items = [i for i in _children(f"{route}::") if i["_key"] not in tab_ids]
    for alias in ALIASES.get(route, ()):
        page_items += _children(f"{alias}::")
    strip = lambda items: [{k: v for k, v in i.items() if k != "_key"} for i in items]  # noqa: E731
    return {"description": _entry(route), "items": strip(page_items),
            "tabs": {tid: {"description": t["description"], "items": strip(t["items"])} for tid, t in tabs.items()}}
