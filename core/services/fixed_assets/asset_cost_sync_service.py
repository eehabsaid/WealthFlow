# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

from decimal import Decimal
from core.models import AssetRenovation, AssetAcquisitionCost
from core.constants import REAL_ESTATE_ASSET_TYPES
from core.services.expenses.expense_service import _apply_expense_balance_delta


def _sync_asset_renovations(asset, items):
    """Update-or-create renovation rows by id instead of delete-and-recreate,
    so a row's id (and its mirrored Expense row — see
    asset_expense_mirror_service) stays stable across saves instead of
    churning on every unrelated asset edit. Mirrors _sync_asset_furniture's
    update-or-create pattern."""
    existing = {r.id: r for r in AssetRenovation.objects.filter(asset=asset)}

    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES:
        items = []

    keep_ids = set()
    for item in items or []:
        payment_method = item.get("payment_method", "Cash")
        bank_id = item.get("bank_id")
        amount_egp = item.get("amount_egp", 0)
        row = existing.get(item.get("id"))

        if row:
            _apply_expense_balance_delta(row.payment_method, row.bank_id, Decimal(str(row.amount_egp or 0)))
            row.furniture_id = item.get("furniture_id")
            row.date = item.get("date") or None
            row.category = item.get("category", "")
            row.description = item.get("description", "")
            row.amount_egp = amount_egp
            row.usd_rate = item.get("usd_rate", 0)
            row.amount_usd = item.get("amount_usd", 0)
            row.payment_method = payment_method
            row.bank_id = bank_id
            row.notes = item.get("notes", "")
            row.save()
        else:
            row = AssetRenovation.objects.create(
                asset=asset,
                furniture_id=item.get("furniture_id"),
                date=item.get("date") or None,
                category=item.get("category", ""),
                description=item.get("description", ""),
                amount_egp=amount_egp,
                usd_rate=item.get("usd_rate", 0),
                amount_usd=item.get("amount_usd", 0),
                payment_method=payment_method,
                bank_id=bank_id,
                notes=item.get("notes", ""),
            )
        _apply_expense_balance_delta(payment_method, bank_id, -Decimal(str(amount_egp or 0)))
        keep_ids.add(row.id)

    for old_id, old in existing.items():
        if old_id not in keep_ids:
            _apply_expense_balance_delta(old.payment_method, old.bank_id, Decimal(str(old.amount_egp or 0)))
            old.delete()


def _sync_asset_acquisition_costs(asset, items):
    """Update-or-create acquisition cost rows by id — same stable-id
    rationale as _sync_asset_renovations."""
    existing = {c.id: c for c in AssetAcquisitionCost.objects.filter(asset=asset)}

    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES:
        items = []

    keep_ids = set()
    for item in items or []:
        payment_method = item.get("payment_method", "Cash")
        bank_id = item.get("bank_id")
        amount_egp = item.get("amount_egp") or 0
        row = existing.get(item.get("id"))

        if row:
            _apply_expense_balance_delta(row.payment_method, row.bank_id, Decimal(str(row.amount_egp or 0)))
            row.date = item.get("date") or None
            row.category = item.get("category", "")
            row.description = item.get("description", "")
            row.amount_egp = amount_egp
            row.usd_rate = item.get("usd_rate") or 0
            row.amount_usd = item.get("amount_usd") or 0
            row.payment_method = payment_method
            row.bank_id = bank_id
            row.notes = item.get("notes", "")
            row.save()
        else:
            row = AssetAcquisitionCost.objects.create(
                asset=asset,
                date=item.get("date") or None,
                category=item.get("category", ""),
                description=item.get("description", ""),
                amount_egp=amount_egp,
                usd_rate=item.get("usd_rate") or 0,
                amount_usd=item.get("amount_usd") or 0,
                payment_method=payment_method,
                bank_id=bank_id,
                notes=item.get("notes", ""),
            )
        _apply_expense_balance_delta(payment_method, bank_id, -Decimal(str(amount_egp or 0)))
        keep_ids.add(row.id)

    for old_id, old in existing.items():
        if old_id not in keep_ids:
            _apply_expense_balance_delta(old.payment_method, old.bank_id, Decimal(str(old.amount_egp or 0)))
            old.delete()
