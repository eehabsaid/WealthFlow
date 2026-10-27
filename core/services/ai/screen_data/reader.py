"""Runs one catalogued endpoint exactly as the app's own screen does: the real view, for the current user, with the query the
model chose. Same code path and same live data as the screen, so the numbers are the screen's numbers."""

from __future__ import annotations

import json
import logging
from urllib.parse import parse_qsl, urlsplit

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import RequestFactory
from django.urls import Resolver404, resolve

from . import catalog, policy, shrink

logger = logging.getLogger("core.ai.pipeline")
RESULT_CHARS = 6500


def _query(raw, from_path: str) -> dict:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw) if raw.strip().startswith("{") else dict(parse_qsl(raw))
        except ValueError:
            raw = {}
    merged = dict(parse_qsl(from_path))
    for key, value in (raw if isinstance(raw, dict) else {}).items():
        if value is None or value == "":
            continue
        merged[str(key)] = ",".join(map(str, value)) if isinstance(value, (list, tuple)) else \
            str(value).lower() if isinstance(value, bool) else str(value)
    return merged


def _error(message: str, **extra) -> dict:
    return {"error": message, **extra}


def read(user, path: str, query) -> dict:
    parts = urlsplit(str(path or "").strip())
    url = parts.path if parts.path.startswith("/") else "/" + parts.path
    if not policy.allowed(url):
        return _error("this path is not available to the assistant; search for the screen's data with app_screen_data(search=...)")
    try:
        match = resolve(url)
    except Resolver404:
        return _error(f"no such endpoint: {url}. Use search=... to find the right path, and put ids into the path.")
    endpoint = catalog.for_callback(match.func)
    if endpoint is None:
        return _error("this path is not a readable data endpoint; search with app_screen_data(search=...)")
    params = _query(query, parts.query)
    request = RequestFactory().get(url, params)
    request.user, request.session = user, SessionStore()
    try:
        response = match.func(request, *match.args, **match.kwargs)
        if hasattr(response, "render"):
            response = response.render()
    except Http404:
        return _error("no such record for this user (404): check the ids in the path", path=url)
    except PermissionDenied:
        return _error("this user is not allowed to read it (403)", path=url)
    except Exception as exc:   # a view failing must reach the model as a message, never as a stack trace
        logger.warning("[AI-SCREEN-DATA] %s failed: %s", url, exc, exc_info=True)
        return _error(f"the screen's calculation failed ({type(exc).__name__}); check the query parameters", path=url, query=params)
    if "json" not in str(response.get("Content-Type", "")).lower():
        return _error("this endpoint does not return data (it returns a file or a page)", path=url)
    try:
        data = json.loads(response.content.decode("utf-8") or "null")
    except ValueError:
        return _error("the endpoint returned unreadable data", path=url)
    if response.status_code >= 400:
        return _error(f"the endpoint answered {response.status_code}", path=url, query=params, answer=shrink.fit(data, 800)[0])
    fitted, notes = shrink.fit(data, RESULT_CHARS)
    out = {"path": url, "query_used": params, "data": fitted}
    if endpoint.params:
        out["query_parameters"] = dict(endpoint.params)
    if notes:
        out["shortened"] = notes
    return out
