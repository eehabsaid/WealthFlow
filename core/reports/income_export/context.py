"""Shared context for the Income Analytics Excel/PDF exports."""
from core.reports.report_context import set_report_base_code
from core.reports.report_utils import get_translations
from core.services.reports.income_analytics import build_income_analytics
from core.services.reports.income_analytics.sources import SOURCES
from core.services.shared.base_currency import get_user_base_code

LANGS = ("en", "ar", "fr", "de")
SOURCE_COLORS = {s["id"]: s["color"] for s in SOURCES}


def income_export_context(request):
    user = request.user
    set_report_base_code(get_user_base_code(user))
    lang = request.GET.get("lang", "en")
    if lang not in LANGS:
        lang = "en"
    t = get_translations(lang)
    data = build_income_analytics(user, request.GET)
    return {"user": user, "lang": lang, "t": t, "data": data}


def income_period_label(data):
    parts = []
    for p in data["periods"]:
        parts.append(str(p["year"]) + (f"-{p['month']:02d}" if p["month"] else ""))
    return "_".join(parts)


def income_filename(data, lang, ext):
    return f"income_{income_period_label(data)}_{lang}.{ext}"


def income_source_label(t, source_id):
    return t.get(f"income_src_{source_id}", source_id)


def income_item_label(t, source_id, key):
    if key.startswith("m") and key[1:2].isdigit():
        from core.services.reports.income_summary_service import MONTH_NAMES

        m = int(key[1:])
        name = MONTH_NAMES[m - 1] if 1 <= m <= 12 else key
        return t.get(f"month_{name}", name)
    if source_id == "cert":
        return f"{t.get('income_cert_no', 'Certificate')} {key}"
    return key
