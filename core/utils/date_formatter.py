"""
Centralized date formatting utility for WealthFlow.
Formats user-visible dates into localized 'dd-mmm-yyyy' format using the stored translation keys month_short_1..month_short_12.

Examples:
  English: 27-Jul-2026 / 05-Jan-2026
  French:  27-juil.-2026 / 05-janv.-2026
  Arabic:  27-يوليو-2026 / 05-يناير-2026
  German:  27-Jul-2026 / 05-Jan-2026
"""

import os
import json
import re
import datetime
from django.conf import settings

_TRANSLATION_CACHE = {}


def get_i18n_dict(lang: str) -> dict:
    """
    Loads and caches static/i18n/{lang}.json translations.
    """
    if not lang:
        lang = "en"
    if lang not in _TRANSLATION_CACHE:
        path = os.path.join(settings.BASE_DIR, "static", "i18n", f"{lang}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                _TRANSLATION_CACHE[lang] = json.load(f)
        except Exception:
            _TRANSLATION_CACHE[lang] = {}
    return _TRANSLATION_CACHE[lang]


def format_date(value, lang: str = None) -> str:
    """
    Formats a date object, datetime object, or date/datetime string into 'dd-mmm-yyyy' localized string.
    Preserves time components if present.
    If parsing fails, returns str(value) safely without raising exceptions.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        val_str = value.strip()
        if not val_str:
            return ""
        if val_str == "-":
            return "-"
    else:
        val_str = str(value)

    try:
        # Determine language if not provided
        if not lang:
            try:
                from core.models.settings import AppSettings
                lang = AppSettings.get("active_language", "en") or "en"
            except Exception:
                lang = "en"

        translations = get_i18n_dict(lang)

        dt = None
        time_part = ""

        # Case 1: Python datetime.datetime object
        if isinstance(value, datetime.datetime):
            dt = value.date()
            if value.hour != 0 or value.minute != 0 or value.second != 0 or value.microsecond != 0:
                if value.second != 0 or value.microsecond != 0:
                    time_part = f" {value.strftime('%H:%M:%S')}"
                else:
                    time_part = f" {value.strftime('%H:%M')}"

        # Case 2: Python datetime.date object
        elif isinstance(value, datetime.date):
            dt = value

        # Case 3: String parsing
        elif isinstance(value, str):
            # Check ISO format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS / YYYY-MM-DD HH:MM:SS
            match_iso = re.match(
                r"^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}:\d{2}(?::\d{2})?))?", val_str
            )
            if match_iso:
                year_i = int(match_iso.group(1))
                month_i = int(match_iso.group(2))
                day_i = int(match_iso.group(3))
                dt = datetime.date(year_i, month_i, day_i)
                if match_iso.group(4):
                    time_part = f" {match_iso.group(4)}"
            else:
                # Check DD-MM-YYYY or DD/MM/YYYY or DD-MM-YYYY HH:MM
                match_dmy = re.match(
                    r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})(?:\s+(\d{2}:\d{2}(?::\d{2})?))?", val_str
                )
                if match_dmy:
                    day_i = int(match_dmy.group(1))
                    month_i = int(match_dmy.group(2))
                    year_i = int(match_dmy.group(3))
                    dt = datetime.date(year_i, month_i, day_i)
                    if match_dmy.group(4):
                        time_part = f" {match_dmy.group(4)}"

        if dt is not None and 1 <= dt.month <= 12:
            month_key = f"month_short_{dt.month}"
            month_name = translations.get(month_key, dt.strftime("%b"))
            day_str = f"{dt.day:02d}"
            year_str = f"{dt.year}"
            return f"{day_str}-{month_name}-{year_str}{time_part}"

    except Exception:
        pass

    return val_str
