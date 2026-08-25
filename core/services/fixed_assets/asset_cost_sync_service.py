# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

from decimal import Decimal
from core.models import AssetRenovation, AssetAcquisitionCost
from core.constants import REAL_ESTATE_ASSET_TYPES
from core.services.expenses.expense_service import _apply_expense_balance_delta


def _sync_asset_renovations(asset, items):
    """Replace all renovations for an asset, reversing the balance delta of any
    existing rows before deleting them and applying the new rows' delta on
    create. Mirrors _sync_asset_furniture's reverse-then-apply pattern so
    payment_method/bank_id changes on save are reflected in the linked
    balance entry, and furniture_id / payment_method / bank_id survive
    the delete-and-recreate cycle used by the whole-asset save."""
    for old in AssetRenovation.objects.filter(asset=asset):
        _apply_expense_balance_delta(old.payment_method, old.bank_id, Decimal(str(old.amount_egp or 0)))
    AssetRenovation.objects.filter(asset=asset).delete()

    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES:
        return

    for item in items or []:
        payment_method = item.get("payment_method", "Cash")
        bank_id = item.get("bank_id")
        amount_egp = item.get("amount_egp", 0)
        AssetRenovation.objects.create(
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

def _sync_asset_acquisition_costs(asset, items):
    """Replace all acquisition costs for an asset. Same reverse-then-apply
    balance pattern as _sync_asset_renovations."""
    for old in AssetAcquisitionCost.objects.filter(asset=asset):
        _apply_expense_balance_delta(old.payment_method, old.bank_id, Decimal(str(old.amount_egp or 0)))
    AssetAcquisitionCost.objects.filter(asset=asset).delete()

    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES:
        return

    for item in items or []:
        payment_method = item.get("payment_method", "Cash")
        bank_id = item.get("bank_id")
        amount_egp = item.get("amount_egp") or 0
        AssetAcquisitionCost.objects.create(
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
