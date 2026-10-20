"""Section plan for an app user guide: one unit per screen of the live app (from app_pages(), so a new screen or tab is
covered automatically), screens with many tabs split into several units, and a deterministic fallback text per unit so
the guide never has a hole when the model fails or time runs out."""

from __future__ import annotations

import json

from .compose_descriptions import page_evidence, slug
from .compose_quality import clean_title

TABS_PER_UNIT = 5
GETTING_STARTED = {"route": "auth", "title": "Signing up and signing in", "open": "/",
                   "actions": ["Create Account", "Login", "Forgot Password", "Restore Account", "Privacy", "Terms"]}
KNOWLEDGE_CHARS = 3500


def units(user) -> list[dict]:
    """[{"title", "evidence" (JSON of the screen/tabs), "fallback" (Markdown)}] for the screens this user may open."""
    from core.authentication.utils.auth_utils import user_is_sysadmin
    from core.services.ai.app_pages import app_pages

    admin = user_is_sysadmin(user)
    out = []
    for page in [GETTING_STARTED, *(p for p in app_pages() if admin or not p.get("admin_only"))]:
        tabs = page.get("tabs") or []
        chunks = [tabs[i:i + TABS_PER_UNIT] for i in range(0, len(tabs), TABS_PER_UNIT)] or [[]]
        for n, chunk in enumerate(chunks, 1):
            title = clean_title(page.get("title") or page.get("route") or "")
            heading = title if n == 1 else ""     # a screen split in parts is ONE chapter: only its first part carries the "## title"
            label = f"{title} ({n}/{len(chunks)})" if len(chunks) > 1 else title   # for the progress line only, never for the model or the file
            shown = _evidence(page, chunk)
            shown_tabs = {t.get("name"): t for t in shown.get("tabs", [])}
            tab_items = [{**t, **{k: v for k, v in shown_tabs.get(t.get("name"), {}).items() if k in ("description", "dialogs")}} for t in chunk]
            out.append({"title": title, "label": label, "part": (n, len(chunks)), "heading": heading, "page": str(page.get("title") or page.get("route") or ""), "tabs": [t.get("name", "") for t in chunk],
                        "tab_items": tab_items,
                        "evidence": json.dumps(shown, ensure_ascii=False), "fallback": _fallback(heading, shown, tab_items)})
    return out


def _evidence(page: dict, chunk: list) -> dict:
    """The screen as the model sees it: its documented purpose and steps, then each tab and dialog with ITS documented text."""
    found = page_evidence(str(page.get("route")), [str(t.get("id") or "") for t in chunk])
    names = {slug(a): a for a in page.get("actions") or []}
    for tab in chunk:
        names.update({slug(a): a for a in tab.get("actions") or []})

    def named(items: list) -> list:
        return [{**i, "name": names.get(slug(i["name"]), i["name"])} for i in items]

    shown = {k: v for k, v in page.items() if k not in ("tabs", "actions")}
    shown.update({"description": found["description"], "dialogs": named(found["items"]) or page.get("actions") or []})
    shown["tabs"] = [{"name": t.get("name"), "description": found["tabs"][str(t.get("id") or "")]["description"],
                      "dialogs": named(found["tabs"][str(t.get("id") or "")]["items"]) or t.get("actions") or []} for t in chunk]
    return {k: v for k, v in shown.items() if v not in (None, [], {})}


def _described(item: dict) -> list[str]:
    """purpose + numbered steps of one documented entry (screen, tab or dialog)."""
    desc = item.get("description") if "description" in item else item
    if not isinstance(desc, dict) or not desc.get("purpose"):
        return []
    return [str(desc["purpose"]), "", *[f"{n}. {s}" for n, s in enumerate(desc.get("steps") or [], 1)]]


def _fallback(heading: str, shown: dict, chunk: list) -> str:
    """The unit written from the app's own documented text (used when the model skipped it or time ran out)."""
    lines = [*([f"## {heading}", ""] if heading else [])]
    if heading:
        lines += _described(shown) or [f"Open it from the menu (route {shown.get('open') or '#' + str(shown.get('route'))})."]
    dialogs = shown.get("dialogs") or []
    if dialogs and not chunk:
        lines += ["", "What you can do here:", *[f"- {d['name']}: {d['purpose']}" if isinstance(d, dict) and d.get("purpose") else f"- {d.get('name') if isinstance(d, dict) else d}" for d in dialogs]]
    for tab in chunk:
        lines += ["", tab_fallback(tab)]
    return "\n".join(lines).strip()


def tab_fallback(tab: dict) -> str:
    """One tab from the app's own documented text, else its action list (used when the model skipped or could not write it)."""
    lines = [f"### {tab.get('name', '')}", *_described(tab)]
    for d in tab.get("dialogs") or []:
        if isinstance(d, dict):
            lines.append(f"- {d['name']}: {d['purpose']}" if d.get("purpose") else f"- {d['name']}")
        else:
            lines.append(f"- {d}")
    return "\n".join(lines)


def _norm(text: str) -> str:
    return "".join(ch for ch in str(text).lower().replace("&", "and") if ch.isalnum())


def dedupe_headings(markdown: str) -> str:
    """A heading right after the same heading (a model that repeats the tab name, a fallback added next to the model's text) is dropped."""
    out: list[str] = []
    last = ""
    for line in markdown.splitlines():
        if line.lstrip().startswith("#"):
            key = _norm(line)
            if key and key == last:
                continue
            last = key
        elif line.strip():
            last = ""
        out.append(line)
    return "\n".join(out)


def missing_tabs(unit: dict, text: str) -> list[dict]:
    """The unit's tabs the written section does not cover: no heading carries the tab's name (a model that writes five
    tabs in one reply tends to drop the last ones), and the name is not mentioned twice in the body either."""
    headings = [_norm(line.lstrip("#")) for line in text.splitlines() if line.lstrip().startswith("#")]
    body = _norm(text)
    return [t for t in unit["tab_items"] if _norm(t.get("name")) and not any(_norm(t["name"]) in h for h in headings)
            and body.count(_norm(t["name"])) < 2]


def knowledge(user, unit: dict, tab: dict | None = None) -> str:
    """The app guide's text about this unit (or one of its tabs): what the screen does, where its data comes from, capped."""
    from core.services.ai.domains import app_enabled
    from core.services.ai.tools import validate_and_execute_tool

    from .loop_helpers import result_text

    if not app_enabled():   # technical information is switched off (Settings > AI Advisor > Chat domains): the guide uses the documented screen text only
        return ""
    query = " ".join([unit["page"], tab.get("name", "")] if tab else [unit["page"], *unit["tabs"]])[:120]
    try:
        _, res = validate_and_execute_tool("app_knowledge_search", {"query": query}, user)
        return result_text(res, KNOWLEDGE_CHARS)
    except Exception:  # noqa: BLE001 - extra evidence only
        return ""
