"""OpenAI-compatible speech API client using only Python's standard library."""

import json
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .settings import get_speech_config


def _request(url, body, headers, timeout):
    req = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as response:
            return response.read(), response.headers.get("Content-Type", "application/octet-stream")
    except HTTPError as exc:
        raise RuntimeError(f"Speech API returned HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Speech API connection failed or timed out") from None


def _auth_headers(cfg):
    headers = {"Accept": "application/json"}
    if cfg["api_key"]:
        headers["Authorization"] = f"Bearer {cfg['api_key']}"
    return headers


def transcribe_audio(audio_bytes, filename, content_type):
    cfg = get_speech_config("stt", include_secret=True)
    if not cfg["enabled"] or not cfg["is_configured"]:
        raise RuntimeError("Speech-to-text is disabled or not configured")
    boundary = f"wealthflow-{uuid.uuid4().hex}"
    fields = {"model": cfg["model"], "response_format": "json"}
    if cfg.get("language") and cfg["language"] != "auto":
        fields["language"] = cfg["language"]
    parts = []
    for name, value in fields.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    safe_name = filename.replace('"', "")[:120] or "recording.webm"
    parts.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{safe_name}\"\r\nContent-Type: {content_type}\r\n\r\n").encode() + audio_bytes + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    headers = _auth_headers(cfg)
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    raw, _ = _request(cfg["endpoint"], body, headers, cfg["timeout"])
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("STT endpoint did not return a JSON transcription") from exc
    text = payload.get("text") or payload.get("transcription") or payload.get("output_text")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("STT response did not contain a transcription text field")
    return text.strip()


def synthesize_speech(text):
    cfg = get_speech_config("tts", include_secret=True)
    if not cfg["enabled"] or not cfg["is_configured"]:
        raise RuntimeError("Text-to-speech is disabled or not configured")
    payload = {"model": cfg["model"], "input": text, "response_format": "mp3"}
    if cfg["voice"]:
        payload["voice"] = cfg["voice"]
    headers = _auth_headers(cfg)
    headers["Content-Type"] = "application/json"
    raw, mime = _request(cfg["endpoint"], json.dumps(payload).encode(), headers, cfg["timeout"])
    if not raw:
        raise RuntimeError("TTS endpoint returned an empty audio response")
    if "json" in mime.lower():
        raise RuntimeError("TTS endpoint returned JSON instead of audio; configure an OpenAI-compatible audio endpoint")
    return raw, mime


def test_speech_endpoint(kind, overrides=None):
    cfg = get_speech_config(kind, include_secret=True)
    overrides = overrides or {}
    for field in ("provider", "endpoint", "model", "timeout", "voice"):
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
    headers = _auth_headers(cfg)
    headers["Content-Type"] = "application/json"
    payload = {"model": cfg["model"], "input": "WealthFlow speech connection test", "response_format": "mp3"}
    try:
        raw, mime = _request(cfg["endpoint"], json.dumps(payload).encode(), headers, min(cfg["timeout"], 15))
        return {"ok": bool(raw), "detail": f"Endpoint responded ({mime})"}
    except RuntimeError as exc:
        # STT endpoints commonly reject a JSON probe but the HTTP response still confirms reachability.
        message = str(exc)
        if any(code in message for code in ("HTTP 400", "HTTP 405", "HTTP 415", "HTTP 422")):
            return {"ok": True, "detail": "Endpoint is reachable; test with a real recording to verify its request format."}
        raise
