"""What to photograph: every documented screen of the app the user may open, and each of its tabs (the same list the guide is
written from, ai/doc_engine/inventory.json via app_pages)."""

from __future__ import annotations

from ai.services.guide_shots import store
from ai.services.investigation.compose_quality import clean_title, norm


def targets(user, blurred: bool) -> list[dict]:
    """[{"key", "route", "title", "tab": None | {"id", "name"}}] in guide order (a screen, then its tabs)."""
    from ai.host import user_is_sysadmin
    from ai.services.app_pages import app_pages

    admin, out = user_is_sysadmin(user), []
    for page in app_pages():
        if page.get("admin_only") and not admin:
            continue
        route, title = str(page["route"]), clean_title(page.get("title") or page["route"])
        out.append({"key": store.key_for(route, "", blurred), "route": route, "title": title, "tab": None})
        for tab in page.get("tabs") or []:
            name = str(tab.get("name") or "")
            out.append({"key": store.key_for(route, str(tab.get("id") or name), blurred), "route": route, "title": name,
                        "tab": {"id": str(tab.get("id") or ""), "name": name}})
    return out


def chapters(plan: list[dict]) -> list[tuple[dict, list[dict]]]:
    """[(screen target, [its tab targets])] in guide order."""
    out: list[tuple[dict, list[dict]]] = []
    for t in plan:
        if t["tab"] is None:
            out.append((t, []))
        elif out:
            out[-1][1].append(t)
    return out


def same(a: str, b: str) -> bool:
    return bool(norm(a)) and norm(a) == norm(b)
