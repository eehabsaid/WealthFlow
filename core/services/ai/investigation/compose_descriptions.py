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


@lru_cache(maxsize=1)
def _labels() -> dict:
    """The English interface texts (static/i18n/en.json): a dialog documented under an i18n key is named by the label the user sees."""
    try:
        data = json.loads((Path(settings.BASE_DIR) / "static" / "i18n" / "en.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, str)}


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
    out, seen = [], set()
    for key in _all():
        if key.startswith(prefix) and "::" not in key[len(prefix):]:
            tail = key[len(prefix):]
            label = _labels().get(tail, "").strip() or str(_all()[key].get("title") or "").strip()   # an interface label, else the entry's own "title"
            name = label if 0 < len(label) <= 40 else re.sub(r"\d+$", "", tail.replace("_", " ").replace("-", " ").strip()).strip().title()   # "add_perdiem2" is a second text of "Add Perdiem"
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            out.append({"name": name, "_key": tail, "_labelled": 0 < len(label) <= 40, **(_entry(key) or {})})
    return out


def _same(a: dict | None, b: dict | None) -> bool:
    return bool(a and b and a.get("purpose") and a.get("purpose") == b.get("purpose") and a.get("steps") == b.get("steps"))


def _unique(items: list[dict], parent: dict | None) -> list[dict]:
    """The documented items without copies: an item with the very text of its tab / page (a placeholder copied into each of
    its sub-tabs) or of another item is the same fact twice, and the guide would print an empty or doubled heading for it.
    Of two identical items the one named by an interface label (what the user sees) is kept, not the one named from a key."""
    kept: list[dict] = []
    for item in items:
        if _same(item, parent):
            continue
        twin = next((k for k in kept if _same(k, item)), None)
        if twin is None:
            kept.append(item)
        elif item["_labelled"] and not twin["_labelled"]:
            kept[kept.index(twin)] = item
    return kept


def page_evidence(route: str, tab_ids: list[str], page_tab_ids: list[str] | None = None, first: bool = True) -> dict:
    """{"description", "items": [...]} for the page itself and, per tab id, {"description", "items"}.
    page_tab_ids: EVERY tab of the page. A page split into parts lists only its own tabs in tab_ids; the tabs of the other parts are
    documented under the same "route::" prefix and must not come back as page-level "dialogs" (the guide printed them as
    "Settings Aiadvisor" and wrote each tab twice). first: the page's own text and dialogs belong to its first part only."""
    tabs = {tid: {"description": _entry(f"{route}::{tid}"), "items": _children(f"{route}::{tid}::")} for tid in tab_ids}
    known = set(tab_ids) | set(page_tab_ids or [])
    page_items = [i for i in _children(f"{route}::") if i["_key"] not in known] if first else []
    for alias in ALIASES.get(route, ()) if first else ():
        page_items += _children(f"{alias}::")
    strip = lambda items: [{k: v for k, v in i.items() if k not in ("_key", "_labelled")} for i in items]  # noqa: E731
    page = _entry(route) if first else None
    return {"description": page, "items": strip(_unique(page_items, page)),
            "tabs": {tid: {"description": t["description"], "items": strip(_unique(t["items"], t["description"]))} for tid, t in tabs.items()}}
