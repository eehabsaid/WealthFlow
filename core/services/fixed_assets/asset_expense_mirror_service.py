# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false
"""Keeps a read-only Expense mirror row in sync with a fixed-asset
renovation, acquisition cost, or furniture record, so that spend
accumulates in Expenses/dashboards like a manual entry — without ever
touching balance, which stays single-sourced from the asset record.
Called only from the signal receivers in fixed_assets_history.py.

Sync mechanics live in core.services.shared.expense_mirror_engine and
are shared with other domains (e.g. core.services.balance's credit
card payment mirror) — this file only owns Fixed-Assets-specific
naming/field mapping.
"""

from core.services.shared.expense_mirror_engine import (
    delete_mirror,
    get_or_create_mirror_subcategory,
    sync_mirror,
)

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


def _get_or_create_fixed_assets_subcategory(source_type):
    return get_or_create_mirror_subcategory(
        FIXED_ASSETS_CATEGORY_NAME,
        FIXED_ASSETS_CATEGORY_ICON,
        FIXED_ASSETS_CATEGORY_COLOR,
        SUBCATEGORY_NAME_BY_SOURCE[source_type],
    )


def _sync_mirror(source_type, source_id, *, date_value, description, amount_egp, payment_method, bank_id, notes):
    category, subcategory = _get_or_create_fixed_assets_subcategory(source_type)
    return sync_mirror(
        source_type,
        source_id,
        date_value=date_value,
        description=description,
        amount_egp=amount_egp,
        payment_method=payment_method,
        bank_id=bank_id,
        notes=notes,
        category=category,
        subcategory=subcategory,
    )


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
    delete_mirror(SOURCE_RENOVATION, renovation_id)


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
    delete_mirror(SOURCE_ACQUISITION_COST, acquisition_cost_id)


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
    delete_mirror(SOURCE_FURNITURE, furniture_id)
