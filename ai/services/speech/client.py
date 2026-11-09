"""OpenAI-compatible speech transport and speech-to-text, using only Python's standard library."""

import json
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ai.services.speech.settings import get_speech_config


def _request(url, body, headers, timeout, retries=0):
    req = Request(url, data=body, headers=headers, method="POST")
    for attempt in range(retries + 1):
        try:
            with urlopen(req, timeout=timeout) as response:
                return response.read(), response.headers.get("Content-Type", "application/octet-stream")
        except HTTPError as exc:
            try:
                detail = exc.read(2048).decode("utf-8", errors="replace").strip()
            except OSError:
                detail = ""
            if exc.code in {500, 502, 503, 504} and attempt < retries:
                time.sleep(attempt + 1)
                continue
            detail = " ".join(detail.split())[:500]
            suffix = f": {detail}" if detail else ""
            raise RuntimeError(f"Speech API returned HTTP {exc.code}{suffix}") from None
        except (URLError, TimeoutError, OSError):
            if attempt < retries:
                time.sleep(attempt + 1)
                continue
            raise RuntimeError("Speech API connection failed or timed out") from None
    raise RuntimeError("Speech API request failed")


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
    raw, _ = _request(cfg["endpoint"], body, headers, cfg["timeout"], retries=2)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("STT endpoint did not return a JSON transcription") from exc
    text = payload.get("text") or payload.get("transcription") or payload.get("output_text")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("STT response did not contain a transcription text field")
    return text.strip()
