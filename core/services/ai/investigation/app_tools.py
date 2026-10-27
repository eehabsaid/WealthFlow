"""App-structure tools for every user (no source code): screens/routes, UI text in the four languages, ready-made verified figures.

Django URL -> view paths are code layout, so they are added only for the sysadmin (code access)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from core.services.ai.app_pages import app_pages

from . import code_tools

LANGS = ("en", "ar", "fr", "de")
MAX_HITS = 25


def routes(user, params):
    from core.authentication.utils.auth_utils import user_is_sysadmin

    admin = user_is_sysadmin(user)
    query = str(params.get("query") or "").strip().lower()
    pages = [p for p in app_pages() if admin or not p.get("admin_only")]
    if query:
        pages = [p for p in pages if query in json.dumps(p, ensure_ascii=False).lower()]
    out = {"query": query, "screens": pages[:30], "total": len(pages),
           "note": "each screen: route (open as #route), tabs and the dialogs/actions inside it"}
    if not pages:
        out["note"] = "no screen matched; try one word of its name, or call app_routes without a query to list all screens"
    if admin and code_tools.code_access_allowed(user):
        from core.services.ai.tools.app_structure import _get_live_django_routes

        out["django_routes"] = [r for r in _get_live_django_routes() if not query or query in f"{r['route']} {r['name']}".lower()][:40]
    return out


@lru_cache(maxsize=4)
def _strings(lang: str) -> dict:
    try:
        with open(Path(settings.BASE_DIR) / "static" / "i18n" / f"{lang}.json", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in data.items() if isinstance(v, str)}


def i18n_search(user, params):
    term = str(params.get("term") or "").strip().lower()
    lang = str(params.get("lang") or "en").strip().lower()
    if len(term) < 2:
        return {"error": "term is required, e.g. 'exchange rate' or a UI key such as 'nav_gold_price'"}
    if lang not in LANGS:
        return {"error": f"lang must be one of {', '.join(LANGS)}"}
    hits = [{"key": k, "text": v[:160]} for k, v in _strings(lang).items() if term in k.lower() or term in v.lower()]
    return {"term": term, "lang": lang, "matches": hits[:MAX_HITS], "total": len(hits),
            **({} if hits else {"note": "no UI text matched; try another word or another lang"})}


def computed_figures(user, params):
    """The same router + executors the instant answers use (net worth, balances, averages, forecasts ...), as exact rows."""
    from core.services.ai.query_engine import verified_for_model

    question = str(params.get("question") or "").strip()
    if not question:
        return {"error": "question is required, e.g. 'what is my net worth' or 'average monthly expenses in 2026'"}
    figures = verified_for_model(user, question)
    if not figures:
        return {"question": question, "figures": None,
                "note": "no ready-made computation for this question; use app_data_models + app_data_query to compute it from the records"}
    return {"question": question, "figures": figures,
            "note": "quick figures only. If the question asks what a screen shows or calculates (a projection, forecast, cash flow, "
                    "a figure for a future date), read it with app_screen_data instead and answer from that."}
