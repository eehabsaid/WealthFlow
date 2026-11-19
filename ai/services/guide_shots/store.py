"""Where the captured images live: runtime/guide_shots/<user id>/<key>.jpg. A key is a hash of what was captured, so a user can
only ever read files from their own folder (the view looks in request.user's folder only)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from django.conf import settings

URL = "/api/financial-advisor/ai/guide-shots/{key}/"
_KEY = re.compile(r"^[0-9a-f]{12}$")
URL_RE = re.compile(r"/api/financial-advisor/ai/guide-shots/([0-9a-f]{12})/")


def key_for(route: str, tab: str, blurred: bool) -> str:
    return hashlib.sha1(f"{route}|{tab}|{int(blurred)}".encode()).hexdigest()[:12]


def folder(user_id) -> Path:
    return Path(settings.BASE_DIR) / "runtime" / "guide_shots" / str(int(user_id))


def save(user_id, key: str, data: bytes) -> None:
    folder(user_id).mkdir(parents=True, exist_ok=True)
    (folder(user_id) / f"{key}.jpg").write_bytes(data)


def read(user_id, key: str) -> bytes | None:
    if not _KEY.match(str(key)):
        return None
    try:
        return (folder(user_id) / f"{key}.jpg").read_bytes()
    except OSError:
        return None
