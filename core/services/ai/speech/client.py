"""OpenAI-compatible speech API client using only Python's standard library."""

import io
import json
import os
import uuid
import wave
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .settings import get_speech_config
from .text_prep import speech_chunks


def _request(url, body, headers, timeout):
    req = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as response:
            return response.read(), response.headers.get("Content-Type", "application/octet-stream")
    except HTTPError as exc:
        raise RuntimeError(f"Speech API returned HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError):
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


def _contains_arabic(text):
    return any("\u0600" <= char <= "\u06ff" for char in text)


def _voice_for_text(cfg, text):
    """Select the matching Piper voice for the existing local speech server."""
    voice = str(cfg.get("voice") or "").strip()
    endpoint = str(cfg.get("endpoint") or "").lower()
    model = str(cfg.get("model") or "").lower()
    if not ("127.0.0.1:8765" in endpoint or "localhost:8765" in endpoint):
        return voice
    if "piper" not in model and not voice.lower().endswith(".onnx"):
        return voice
    if _contains_arabic(text):
        return "ar_JO-kareem-medium.onnx"
    if voice.startswith("ar_"):
        return "en_US-lessac-medium.onnx"
    return voice


def _local_arabic_chatterbox_config(cfg, text):
    """Route Arabic from local Piper to the optional local Chatterbox server."""
    endpoint = str(cfg.get("endpoint") or "").lower()
    model = str(cfg.get("model") or "").lower()
    if (not _contains_arabic(text) and not cfg.get("_chatterbox_arabic_response")) or "piper" not in model:
        return None
    if not ("127.0.0.1:8765" in endpoint or "localhost:8765" in endpoint):
        return None
    voice = str(os.environ.get("WF_CHATTERBOX_ARABIC_REFERENCE") or "").strip()
    if not voice.lower().endswith((".wav", ".flac", ".mp3", ".ogg")):
        return None
    routed = dict(cfg)
    routed["endpoint"] = cfg["endpoint"].replace(":8765", ":8766")
    routed["model"] = "chatterbox-multilingual-v3"
    routed["voice"] = voice
    return routed


def _synthesize_chunk(cfg, text):
    chatterbox_cfg = _local_arabic_chatterbox_config(cfg, text)
    request_cfg = chatterbox_cfg or cfg
    voice = chatterbox_cfg["voice"] if chatterbox_cfg else _voice_for_text(cfg, text)
    payload = {
        "model": request_cfg["model"],
        "input": text,
        "response_format": "wav" if chatterbox_cfg else "mp3",
    }
    if voice:
        payload["voice"] = voice
    if chatterbox_cfg:
        payload["language"] = "ar"
    headers = _auth_headers(request_cfg)
    headers["Content-Type"] = "application/json"
    raw, mime = _request(request_cfg["endpoint"], json.dumps(payload).encode(), headers, request_cfg["timeout"])
    if not raw:
        raise RuntimeError("TTS endpoint returned an empty audio response")
    if "json" in mime.lower():
        raise RuntimeError("TTS endpoint returned JSON instead of audio; configure an OpenAI-compatible audio endpoint")
    return raw, mime


def _combine_wav_chunks(chunks):
    """Join WAV responses into one valid WAV file instead of concatenating headers."""
    frames, params = [], None
    for chunk in chunks:
        with wave.open(io.BytesIO(chunk), "rb") as source:
            current = source.getparams()
            if params is None:
                params = current
            elif (current.nchannels, current.sampwidth, current.framerate, current.comptype) != (
                params.nchannels, params.sampwidth, params.framerate, params.comptype
            ):
                raise RuntimeError("TTS endpoint returned incompatible WAV audio chunks")
            frames.append(source.readframes(source.getnframes()))
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setparams(params)
        for frame_data in frames:
            target.writeframesraw(frame_data)
    return output.getvalue()


def synthesize_speech(text):
    """Markdown answer -> (mp3 bytes, mime). Symbols are stripped and long answers are sent in chunks."""
    cfg = get_speech_config("tts", include_secret=True)
    if not cfg["enabled"] or not cfg["is_configured"]:
        raise RuntimeError("Text-to-speech is disabled or not configured")
    chunks = speech_chunks(text)
    if not chunks:
        raise RuntimeError("There is no speakable text")
    reference = str(os.environ.get("WF_CHATTERBOX_ARABIC_REFERENCE") or "").strip()
    if _contains_arabic(text) and reference.lower().endswith((".wav", ".flac", ".mp3", ".ogg")):
        cfg["_chatterbox_arabic_response"] = True
    audio, mime = [], ""
    for chunk in chunks:
        raw, chunk_mime = _synthesize_chunk(cfg, chunk)
        audio.append(raw)
        mime = mime or chunk_mime
    if audio and "wav" in mime.lower():
        return _combine_wav_chunks(audio), mime
    return b"".join(audio), mime


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
