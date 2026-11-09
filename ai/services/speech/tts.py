"""Text-to-speech: picks the configured voice profile for a text and calls its OpenAI-compatible endpoint.

Profiles are plain settings (nothing hardcoded): `tts` is the general profile, `tts_ar` is an optional
profile used when the text is mostly Arabic script (e.g. a Chatterbox server with an Egyptian reference voice).
"""

import io
import json
import wave

from ai.services.speech import client
from ai.services.speech.settings import get_speech_config, speech_runtime_enabled
from ai.services.speech.text_prep import speech_chunks
from ai.services.speech.voice_sample import voice_sample_path

_ARABIC_RANGES = ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF))


def is_arabic_text(text):
    """True when most letters of the text are Arabic script (structural check, no word lists)."""
    letters = [ord(c) for c in str(text or "") if c.isalpha()]
    arabic = sum(1 for cp in letters if any(lo <= cp <= hi for lo, hi in _ARABIC_RANGES))
    return bool(letters) and arabic * 2 >= len(letters)


def _usable(cfg):
    return cfg["enabled"] and cfg["is_configured"]


def _with_uploaded_voice(cfg):
    """A Chatterbox profile with no voice of its own speaks in the voice sample uploaded in Settings (any language)."""
    if "chatterbox" in str(cfg.get("model") or "").lower() and not cfg.get("voice") and (sample := voice_sample_path()):
        return {**cfg, "voice": sample}
    return cfg


def select_tts_profile(text):
    arabic = get_speech_config("tts_ar", include_secret=True)
    if is_arabic_text(text) and _usable(arabic):
        if arabic.get("language") in {"", "auto"}:
            arabic["language"] = "ar"
        return _with_uploaded_voice(arabic)
    general = get_speech_config("tts", include_secret=True)
    if _usable(general):
        return _with_uploaded_voice(general)
    raise RuntimeError("Text-to-speech is disabled or not configured for this text")


def tts_available():
    return speech_runtime_enabled() and any(
        _usable(get_speech_config(kind)) for kind in ("tts", "tts_ar")
    )


def build_tts_payload(cfg, text):
    payload = {"model": cfg["model"], "input": text}
    if cfg.get("voice"):
        payload["voice"] = cfg["voice"]
    if cfg.get("format"):
        payload["response_format"] = cfg["format"]
    if cfg.get("language") and cfg["language"] != "auto":
        payload["language"] = cfg["language"]
    return payload


def _synthesize_chunk(cfg, text):
    headers = client._auth_headers(cfg)
    headers["Content-Type"] = "application/json"
    raw, mime = client._request(cfg["endpoint"], json.dumps(build_tts_payload(cfg, text)).encode(), headers, cfg["timeout"])
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


def has_speakable_text(text):
    return bool(speech_chunks(text))


def synthesize_speech(text):
    """Markdown text -> (audio bytes, mime). One voice profile is chosen for the whole text."""
    chunks = speech_chunks(text)
    if not chunks:
        raise RuntimeError("There is no speakable text")
    cfg = select_tts_profile(" ".join(chunks))
    audio, mime = [], ""
    for chunk in chunks:
        raw, chunk_mime = _synthesize_chunk(cfg, chunk)
        audio.append(raw)
        mime = mime or chunk_mime
    if len(audio) > 1 and "wav" in mime.lower():
        return _combine_wav_chunks(audio), mime
    return b"".join(audio), mime
