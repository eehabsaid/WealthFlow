"""Sysadmin endpoint diagnostics for the configured speech services."""

import json

from ai.services.speech import client
from ai.services.speech.settings import get_speech_config
from ai.services.speech.tts import build_tts_payload

_REACHABLE_CODES = ("HTTP 400", "HTTP 405", "HTTP 415", "HTTP 422")


def test_speech_endpoint(kind, overrides=None):
    cfg = get_speech_config(kind, include_secret=True)
    overrides = overrides or {}
    for field in ("provider", "endpoint", "model", "timeout", "voice", "language", "format"):
        key = f"speech_{kind}_{field}"
        if key in overrides:
            cfg[field] = str(overrides[key] or "").strip()
    submitted_key = str(overrides.get(f"speech_{kind}_api_key") or "").strip()
    if submitted_key and "••••" not in submitted_key:
        cfg["api_key"] = submitted_key
    try:
        cfg["timeout"] = max(1, min(300, int(cfg["timeout"])))
    except (ValueError, TypeError):
        cfg["timeout"] = 60
    if not cfg["endpoint"] or not cfg["model"]:
        raise RuntimeError("Configure the endpoint and model first")
    headers = client._auth_headers(cfg)
    headers["Content-Type"] = "application/json"
    payload = build_tts_payload(cfg, "WealthFlow speech connection test")
    try:
        raw, mime = client._request(cfg["endpoint"], json.dumps(payload).encode(), headers, cfg["timeout"])
        return {"ok": bool(raw), "detail": f"Endpoint responded ({mime})"}
    except RuntimeError as exc:
        # STT endpoints commonly reject a JSON probe but the HTTP response still confirms reachability.
        if any(code in str(exc) for code in _REACHABLE_CODES):
            return {"ok": True, "detail": "Endpoint is reachable; test with a real recording to verify its request format."}
        raise
