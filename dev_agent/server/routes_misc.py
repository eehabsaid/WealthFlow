"""Health, state, settings, API keys (values are never returned), model list, shutdown."""

from __future__ import annotations

import json
import os
import re
import urllib.request

from .. import __version__
from ..settings.store import Settings
from .http import HttpError, Req, Resp


def health(r: Req):
    return {"ok": True, "version": __version__, "project": str(r.project.root), "pid": os.getpid()}


def state(r: Req):
    settings = Settings(r.project).load()
    return {**r.service.state(), "provider": settings["provider"], "model": settings["model"]}


def get_settings(r: Req):
    return Settings(r.project).load()


def put_settings(r: Req):
    return Settings(r.project).update(r.field("values", dict))


def keys_status(r: Req):
    return {"keys": r.keys.status(), "backend": r.keys.store.backend}


def keys_put(r: Req):
    return {"stored_in": r.keys.set(r.match["provider"], r.field("value"))}


def keys_delete(r: Req):
    r.keys.delete(r.match["provider"])
    return {"ok": True}


def keys_unlock(r: Req):
    r.keys.unlock(r.field("passphrase"))
    return {"keys": r.keys.status()}


def models(r: Req):
    settings = Settings(r.project).load()
    provider = r.query.get("provider") or settings["provider"]
    if provider != "ollama":
        return {"provider": provider, "models": [], "note": "type the model name; only Ollama can be listed"}
    base = settings["providers"]["ollama"]["base_url"].rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=4) as response:
            names = sorted(m["name"] for m in json.loads(response.read().decode("utf-8")).get("models", []))
    except (OSError, ValueError, KeyError) as exc:
        raise HttpError(502, "provider", f"cannot list Ollama models: {exc}") from exc
    return {"provider": provider, "models": names}


def shutdown(r: Req):
    r.server.request_shutdown()
    return Resp({"ok": True})


ROUTES = [
    ("GET", re.compile(r"/api/health"), health),
    ("GET", re.compile(r"/api/state"), state),
    ("GET", re.compile(r"/api/settings"), get_settings),
    ("PUT", re.compile(r"/api/settings"), put_settings),
    ("GET", re.compile(r"/api/keys"), keys_status),
    ("POST", re.compile(r"/api/keys/unlock"), keys_unlock),
    ("PUT", re.compile(r"/api/keys/(?P<provider>[a-z]+)"), keys_put),
    ("DELETE", re.compile(r"/api/keys/(?P<provider>[a-z]+)"), keys_delete),
    ("GET", re.compile(r"/api/models"), models),
    ("POST", re.compile(r"/api/shutdown"), shutdown),
]
