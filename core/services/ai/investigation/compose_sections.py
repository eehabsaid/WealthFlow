"""Section plan for an app user guide: one unit per screen of the live app (from app_pages(), so a new screen or tab is
covered automatically), screens with many tabs split into several units, and a deterministic fallback text per unit so
the guide never has a hole when the model fails or time runs out."""

from __future__ import annotations

import json

TABS_PER_UNIT = 5
KNOWLEDGE_CHARS = 3500


def units(user) -> list[dict]:
    """[{"title", "evidence" (JSON of the screen/tabs), "fallback" (Markdown)}] for the screens this user may open."""
    from core.authentication.utils.auth_utils import user_is_sysadmin
    from core.services.ai.app_pages import app_pages

    admin = user_is_sysadmin(user)
    out = []
    for page in (p for p in app_pages() if admin or not p.get("admin_only")):
        tabs = page.get("tabs") or []
        chunks = [tabs[i:i + TABS_PER_UNIT] for i in range(0, len(tabs), TABS_PER_UNIT)] or [[]]
        for n, chunk in enumerate(chunks, 1):
            title = str(page.get("title") or page.get("route") or "")
            if len(chunks) > 1:
                title = f"{title} ({n}/{len(chunks)})"
            shown = {**{k: v for k, v in page.items() if k != "tabs"}, **({"tabs": chunk} if chunk else {})}
            out.append({"title": title, "page": str(page.get("title") or page.get("route") or ""), "tabs": [t.get("name", "") for t in chunk],
                        "tab_items": chunk,
                        "evidence": json.dumps(shown, ensure_ascii=False), "fallback": _fallback(title, page, chunk)})
    return out


def _fallback(title: str, page: dict, chunk: list) -> str:
    lines = [f"## {title}", "", f"Open it from the menu (route {page.get('open') or '#' + str(page.get('route'))})."]
    if page.get("actions") and not chunk:
        lines += ["", "What you can do here:", *[f"- {a}" for a in page["actions"]]]
    for tab in chunk:
        lines += ["", tab_fallback(tab)]
    return "\n".join(lines)


def tab_fallback(tab: dict) -> str:
    """One tab from the app's own tab/action list (used when the model skipped or could not write it)."""
    return "\n".join([f"### {tab.get('name', '')}", *([f"- {a}" for a in tab.get("actions") or []] or ["- Review the records on this tab."])])


def _norm(text: str) -> str:
    return "".join(ch for ch in str(text).lower().replace("&", "and") if ch.isalnum())


def missing_tabs(unit: dict, text: str) -> list[dict]:
    """The unit's tabs the written section does not cover: no heading carries the tab's name (a model that writes five
    tabs in one reply tends to drop the last ones), and the name is not mentioned twice in the body either."""
    headings = [_norm(line.lstrip("#")) for line in text.splitlines() if line.lstrip().startswith("#")]
    body = _norm(text)
    return [t for t in unit["tab_items"] if _norm(t.get("name")) and not any(_norm(t["name"]) in h for h in headings)
            and body.count(_norm(t["name"])) < 2]


def knowledge(user, unit: dict, tab: dict | None = None) -> str:
    """The app guide's text about this unit (or one of its tabs): what the screen does, where its data comes from, capped."""
    from core.services.ai.tools import validate_and_execute_tool

    from .loop_helpers import result_text

    query = " ".join([unit["page"], tab.get("name", "")] if tab else [unit["page"], *unit["tabs"]])[:120]
    try:
        _, res = validate_and_execute_tool("app_knowledge_search", {"query": query}, user)
        return result_text(res, KNOWLEDGE_CHARS)
    except Exception:  # noqa: BLE001 - extra evidence only
        return ""
