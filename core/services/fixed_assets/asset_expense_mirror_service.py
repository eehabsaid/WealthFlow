# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false
"""Keeps a read-only Expense mirror row in sync with a fixed-asset
renovation, acquisition cost, or furniture record, so that spend
accumulates in Expenses/dashboards like a manual entry — without ever
touching balance, which stays single-sourced from the asset record.
Called only from the signal receivers in fixed_assets_history.py.
"""

from datetime import date as _date
from decimal import Decimal

from django.utils.dateparse import parse_date

from core.models import Currency, Expense, ExpenseCategory, ExpenseSubcategory

FIXED_ASSETS_CATEGORY_NAME = "Fixed Assets"
FIXED_ASSETS_CATEGORY_ICON = "🏠"
FIXED_ASSETS_CATEGORY_COLOR = "#6f42c1"

SOURCE_RENOVATION = "asset_renovation"
SOURCE_ACQUISITION_COST = "asset_acquisition_cost"
SOURCE_FURNITURE = "asset_furniture"

SUBCATEGORY_NAME_BY_SOURCE = {
    SOURCE_ACQUISITION_COST: "Acquisition Costs",
    SOURCE_RENOVATION: "Renovation",
    SOURCE_FURNITURE: "Furniture",
}

# Expense.payment_method only offers Cash / Card / Bank Transfer / Other;
# the asset-side models additionally allow the distinct choice "Bank" —
# normalize it so the mirrored row renders with a value the Expenses UI
# actually recognizes.
_PAYMENT_METHOD_MAP = {
    "bank": "Bank Transfer",
}


def _map_payment_method(value):
    raw = str(value or "Cash").strip()
    return _PAYMENT_METHOD_MAP.get(raw.lower(), raw or "Cash")


def _normalize_date(value):
    """Asset-side CRUD views sometimes assign the raw request string
    straight to a DateField without parsing, so the in-memory instance
    seen here can hold a str instead of a date — normalize defensively."""
    if isinstance(value, _date):
        return value
    if isinstance(value, str) and value:
        return parse_date(value)
    return None


def _egp_currency():
    return Currency.objects.filter(code__iexact="EGP").order_by("id").first()


def _get_or_create_fixed_assets_subcategory(source_type):
    """Get-or-create the "Fixed Assets" category + matching subcategory by
    name, so mirroring works even before they exist; reuses them as-is
    once the user creates them by hand."""
    category, _ = ExpenseCategory.objects.get_or_create(
        name=FIXED_ASSETS_CATEGORY_NAME,
        defaults={
            "icon": FIXED_ASSETS_CATEGORY_ICON,
            "color_hex": FIXED_ASSETS_CATEGORY_COLOR,
        },
    )
    subcategory_name = SUBCATEGORY_NAME_BY_SOURCE[source_type]
    subcategory, _ = ExpenseSubcategory.objects.get_or_create(
        category=category,
        name=subcategory_name,
    )
    return category, subcategory


def _delete_mirror(source_type, source_id):
    if not source_id:
        return
    Expense.objects.filter(source_type=source_type, source_id=source_id).delete()


def _sync_mirror(source_type, source_id, *, date_value, description, amount_egp, payment_method, bank_id, notes):
    if not source_id:
        return None

    amount = Decimal(str(amount_egp or 0))
    # A zero/blank amount has nothing to show in Expenses — drop any
    # existing mirror instead of leaving a noise $0 row (e.g. a draft
    # renovation row the user hasn't filled in yet).
    if amount <= 0:
        _delete_mirror(source_type, source_id)
        return None

    # AssetAcquisitionCost.date / AssetFurniture.purchase_date can be left
    # blank — default to today rather than skipping the mirror, so the
    # spend is never silently missing from Expenses/dashboards. Once the
    # user fills in the real date, the mirror updates to match it.
    date_value = _normalize_date(date_value) or _date.today()

    category, subcategory = _get_or_create_fixed_assets_subcategory(source_type)
    currency = _egp_currency()

    defaults = {
        "date": date_value,
        "year": date_value.year,
        "month": date_value.month,
        "category": category,
        "subcategory": subcategory,
        "description": (description or subcategory.name)[:300],
        "amount": amount,
        "exchange_rate": Decimal("1"),
        "amount_egp": amount,
        "currency": currency,
        "bank_id": bank_id,
        "payment_method": _map_payment_method(payment_method),
        "notes": notes,
    }

    exp, _ = Expense.objects.update_or_create(
        source_type=source_type,
        source_id=source_id,
        defaults=defaults,
    )
    return exp


def _compose_description(type_label, detail, free_text):
    """e.g. "Renovation: Painting — Living room paint job" — combines the
    item's type/category with its free-text description instead of
    showing only whichever one happens to be filled in."""
    head = f"{type_label}: {detail}".strip(": ").strip() if detail else type_label
    free_text = (free_text or "").strip()
    if free_text:
        return f"{head} — {free_text}"
    return head


def sync_renovation_mirror(renovation):
    if renovation is None or not renovation.id:
        return None
    asset_name = renovation.asset.name if renovation.asset_id else ""
    description = _compose_description("Renovation", renovation.category, renovation.description)
    notes = f"Auto-generated from asset renovation on '{asset_name}'. Read-only — edit/delete it from the Fixed Assets tab instead."
    return _sync_mirror(
        SOURCE_RENOVATION,
        renovation.id,
        date_value=renovation.date,
        description=description,
        amount_egp=renovation.amount_egp,
        payment_method=renovation.payment_method,
        bank_id=renovation.bank_id,
        notes=notes,
    )


def delete_renovation_mirror(renovation_id):
    _delete_mirror(SOURCE_RENOVATION, renovation_id)


def sync_acquisition_cost_mirror(acquisition_cost):
    if acquisition_cost is None or not acquisition_cost.id:
        return None
    asset_name = acquisition_cost.asset.name if acquisition_cost.asset_id else ""
    description = _compose_description("Acquisition Cost", acquisition_cost.category, acquisition_cost.description)
    notes = f"Auto-generated from asset acquisition cost on '{asset_name}'. Read-only — edit/delete it from the Fixed Assets tab instead."
    return _sync_mirror(
        SOURCE_ACQUISITION_COST,
        acquisition_cost.id,
        date_value=acquisition_cost.date,
        description=description,
        amount_egp=acquisition_cost.amount_egp,
        payment_method=acquisition_cost.payment_method,
        bank_id=acquisition_cost.bank_id,
        notes=notes,
    )


def delete_acquisition_cost_mirror(acquisition_cost_id):
    _delete_mirror(SOURCE_ACQUISITION_COST, acquisition_cost_id)


def sync_furniture_mirror(furniture):
    if furniture is None or not furniture.id:
        return None
    asset_name = furniture.asset.name if furniture.asset_id else ""
    description = _compose_description("Furniture", furniture.category, furniture.name)
    notes = f"Auto-generated from asset furniture on '{asset_name}'. Read-only — edit/delete it from the Fixed Assets tab instead."
    return _sync_mirror(
        SOURCE_FURNITURE,
        furniture.id,
        date_value=furniture.purchase_date,
        description=description,
        amount_egp=furniture.amount_egp,
        payment_method=furniture.payment_method,
        bank_id=furniture.bank_id,
        notes=notes,
    )


def delete_furniture_mirror(furniture_id):
    _delete_mirror(SOURCE_FURNITURE, furniture_id)
