"""The two sysadmin switches (global AISetting rows)."""

from __future__ import annotations

from ai.models import AISetting

KEYS = {"ai_guide_screenshots": "true", "ai_guide_blur": "true"}   # both default ON
_FALSE = ("false", "0", "no", "off")


def flag(key: str) -> bool:
    return str(AISetting.get(key, KEYS[key], user=None) or KEYS[key]).strip().lower() not in _FALSE


def enabled() -> bool:
    return flag("ai_guide_screenshots")


def blur() -> bool:
    return flag("ai_guide_blur")
