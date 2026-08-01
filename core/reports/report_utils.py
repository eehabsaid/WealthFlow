# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
import json as _json
import os
import datetime
from django.conf import settings

MONTH_ORDER = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

def month_sort_key(entry_dict):
    try:
        return MONTH_ORDER.index(entry_dict.get("month", ""))
    except ValueError:
        return len(MONTH_ORDER)

def get_translations(lang):
    path = os.path.join(settings.BASE_DIR, "static", "i18n", f"{lang}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return {}

from core.reports.pdf_font_utils import process_pdf_text

def format_arabic(text):
    return process_pdf_text(text)

def get_text(key, lang, t, default=""):
    return t.get(key, default) if t and key in t else default

def parse_iso_date(value):
    if not value or str(value).strip() in ("", "None"):
        return None
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value).strip())
    except (ValueError, TypeError):
        return None
