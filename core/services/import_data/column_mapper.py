"""Heuristic suggestion of which uploaded column is date/amount/
description/category, based on header names common to Egyptian and Gulf
bank exports (English + Arabic). The user always confirms/edits the
mapping before anything is imported — this only pre-fills a sensible
default.
"""
from datetime import datetime

FIELD_KEYWORDS = {
    "date": ["date", "transaction date", "value date", "posting date", "تاريخ"],
    "amount": ["amount", "debit", "credit", "value", "مبلغ", "قيمة"],
    "description": ["description", "details", "narrative", "memo", "بيان", "الوصف"],
    "category": ["category", "type", "tag", "فئة", "التصنيف"],
}

DATE_FORMATS = [
    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d",
]


def suggest_mapping(headers):
    """Return {field_name: header_or_None} for date/amount/description/category."""
    mapping = {field: None for field in FIELD_KEYWORDS}
    lower_headers = {h: h.strip().lower() for h in headers}
    for field, keywords in FIELD_KEYWORDS.items():
        for header, lowered in lower_headers.items():
            if any(kw in lowered for kw in keywords):
                mapping[field] = header
                break
    return mapping


def parse_date_value(value: str):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    # Excel sometimes hands back an ISO-ish string with a time component.
    try:
        return datetime.fromisoformat(value.split(" ")[0]).date()
    except ValueError:
        return None


def parse_amount_value(value):
    if value in (None, ""):
        return None
    text = str(value).strip().replace(",", "")
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    text = text.replace("+", "")
    try:
        result = abs(float(text))
    except ValueError:
        return None
    return result
