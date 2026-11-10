"""The sysadmin's reference voice for voice cloning. One recording, stored on the server (media/voice_samples/), its path kept in
AISetting. The local Chatterbox server reads the file by path, so it must run on the same computer as WealthFlow."""

from __future__ import annotations

import os
import uuid

from django.conf import settings

from ai.models import AISetting

KEY = "speech_tts_voice_sample"
NAME_KEY = "speech_tts_voice_sample_name"   # the file name as the sysadmin uploaded it, shown in Settings
EXTENSIONS = (".wav", ".flac", ".mp3", ".ogg")
MAX_BYTES = 20 * 1024 * 1024
MIN_BYTES = 20 * 1024     # anything smaller cannot hold a usable voice sample


class VoiceSampleError(ValueError):
    pass


def _folder() -> str:
    return os.path.join(settings.MEDIA_ROOT, "voice_samples")


def voice_sample_path() -> str:
    """The saved sample's path, or '' when none is set or the file is gone."""
    path = str(AISetting.get(KEY, "", user=None) or "")
    return path if path and os.path.isfile(path) else ""


def voice_sample_info() -> dict:
    """What Settings shows: whether a sample is saved, its original file name and size in KB."""
    path = voice_sample_path()
    if not path:
        return {"has_sample": False, "name": "", "size_kb": 0}
    return {"has_sample": True, "name": str(AISetting.get(NAME_KEY, "", user=None) or os.path.basename(path)),
            "size_kb": max(1, os.path.getsize(path) // 1024)}


def save_voice_sample(name: str, raw: bytes) -> str:
    ext = os.path.splitext(name or "")[1].lower()
    if ext not in EXTENSIONS:
        raise VoiceSampleError("unsupported_type")
    if len(raw) > MAX_BYTES:
        raise VoiceSampleError("too_large")
    if len(raw) < MIN_BYTES:
        raise VoiceSampleError("too_small")
    delete_voice_sample()
    os.makedirs(_folder(), exist_ok=True)
    path = os.path.join(_folder(), f"{uuid.uuid4().hex}{ext}")
    with open(path, "wb") as handle:
        handle.write(raw)
    AISetting.set(KEY, path, user=None)
    AISetting.set(NAME_KEY, os.path.basename(name or "")[:120], user=None)
    return path


def delete_voice_sample() -> None:
    path = str(AISetting.get(KEY, "", user=None) or "")
    if path and os.path.isfile(path) and os.path.dirname(os.path.abspath(path)) == os.path.abspath(_folder()):
        os.remove(path)
    AISetting.set(KEY, "", user=None)
    AISetting.set(NAME_KEY, "", user=None)
