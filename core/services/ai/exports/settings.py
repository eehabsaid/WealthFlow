"""Settings for downloadable answers (Settings > AI Advisor, sysadmin only; stored app-wide).

Nothing is stored on the server: a file is built from the saved answer when it is downloaded, so there is no retention
to configure; the link lives as long as the chat message does."""

from __future__ import annotations

from dataclasses import dataclass

from core.models import AppSettings

DEFAULTS = {"ai_file_generation": "true", "ai_file_max_mb": 10, "ai_file_max_rows": 50000}
LIMITS = {"ai_file_max_mb": (1, 50), "ai_file_max_rows": (100, 200000)}
_OFF = ("false", "0", "no", "off")


@dataclass(frozen=True)
class ExportSettings:
    enabled: bool
    max_bytes: int
    max_rows: int


def _number(key: str) -> int:
    low, high = LIMITS[key]
    try:
        return max(low, min(high, int(float(str(AppSettings.get(key, str(DEFAULTS[key]), user=None))))))
    except ValueError:
        return DEFAULTS[key]


def get_settings() -> ExportSettings:
    enabled = str(AppSettings.get("ai_file_generation", DEFAULTS["ai_file_generation"], user=None) or "true").strip().lower() not in _OFF
    return ExportSettings(enabled, _number("ai_file_max_mb") * 1024 * 1024, _number("ai_file_max_rows"))


def exports_enabled() -> bool:
    return get_settings().enabled
