"""Saving the property rate map: the global row and every per-user copy, so they never diverge."""

from __future__ import annotations

import json

from core.models import AppSettings

RATE_MAP_KEY = "property_valuation_rate_map"
RATE_MAP_DESCRIPTION = (
    "Auto-updated EGP/sqm rates by district/governorate. "
    "JSON with keys: by_city, by_governorate, default."
)
_COMPARED_KEYS = ("by_city", "by_governorate", "default")


def _same_rates(raw: str, rate_map: dict) -> bool:
    try:
        saved = json.loads(raw)
    except (TypeError, ValueError):
        return False
    return isinstance(saved, dict) and all(saved.get(k) == rate_map.get(k) for k in _COMPARED_KEYS)


def rate_map_is_current(rate_map: dict) -> bool:
    """True when a global row exists and it and every per-user copy already hold these rates."""
    values = list(AppSettings.objects.filter(key=RATE_MAP_KEY).values_list("value", flat=True))
    return bool(values) and all(_same_rates(v, rate_map) for v in values)


def save_rate_map(rate_map: dict) -> str:
    """Write the map to the global row and to every existing per-user row (valuation reads the
    per-user row first, so a stale copy there would hide a fresh scrape). Returns the saved JSON."""
    new_json = json.dumps(rate_map, ensure_ascii=False, indent=2)
    AppSettings.set(RATE_MAP_KEY, new_json)
    AppSettings.objects.filter(key=RATE_MAP_KEY, owner__isnull=False).update(value=new_json)
    AppSettings.objects.filter(key=RATE_MAP_KEY, description="").update(description=RATE_MAP_DESCRIPTION)
    return new_json
