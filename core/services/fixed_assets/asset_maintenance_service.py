# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

from decimal import Decimal
from core.models import (
    AssetMaintenance,
    AssetInsurance,
    AssetFurniture,
    AssetValuationHistory,

)
from core.constants import (
    REAL_ESTATE_ASSET_TYPES,
    VEHICLE_ASSET_TYPES,
    OTHER_ASSET_TYPES,
)
from core.services.expenses.expense_service import _apply_expense_balance_delta

def _sync_asset_maintenance(asset, items):
    AssetMaintenance.objects.filter(asset=asset).delete()
    if asset.asset_type not in VEHICLE_ASSET_TYPES:
        return

    for item in items or []:
        if not item.get("date"):
            continue
        AssetMaintenance.objects.create(
            asset=asset,
            date=item.get("date"),
            maintenance_type=item.get("type", ""),
            cost=item.get("cost", 0),
            notes=item.get("notes", ""),
        )

def _sync_asset_insurance(asset, items):
    AssetInsurance.objects.filter(asset=asset).delete()
    if asset.asset_type not in VEHICLE_ASSET_TYPES:
        return

    for item in items or []:
        if not item.get("company"):
            continue
        AssetInsurance.objects.create(
            asset=asset,
            company=item.get("company", ""),
            policy_number=item.get("policy_number", ""),
            expiry_date=item.get("expiry_date") or None,
            premium=item.get("premium", 0),
        )

def _sync_asset_furniture(asset, items):
    """Update-or-create furniture rows by id instead of delete-and-recreate,
    so a furniture row's id stays stable across saves. This matters because
    AssetRenovation.furniture is a FK with on_delete=SET_NULL: if furniture
    rows always got new ids, any renovation linked to one would lose that
    link the moment furniture resynced on the same save."""
    existing = {f.id: f for f in AssetFurniture.objects.filter(asset=asset)}

    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES:
        items = []

    keep_ids = set()
    for item in items or []:
        if not item.get("name"):
            continue
        payment_method = item.get("payment_method", "Cash")
        bank_id = item.get("bank_id")
        amount_egp = item.get("amount_egp", 0)
        row = existing.get(item.get("id"))

        if row:
            _apply_expense_balance_delta(row.payment_method, row.bank_id, Decimal(str(row.amount_egp or 0)))
            row.name = item.get("name", "")
            row.category = item.get("category", "")
            row.purchase_date = item.get("purchase_date") or None
            row.amount_egp = amount_egp
            row.usd_rate = item.get("usd_rate", 0)
            row.amount_usd = item.get("amount_usd", 0)
            row.quantity = item.get("quantity", 1)
            row.payment_method = payment_method
            row.bank_id = bank_id
            row.notes = item.get("notes", "")
            row.save()
        else:
            row = AssetFurniture.objects.create(
                asset=asset,
                name=item.get("name", ""),
                category=item.get("category", ""),
                purchase_date=item.get("purchase_date") or None,
                amount_egp=amount_egp,
                usd_rate=item.get("usd_rate", 0),
                amount_usd=item.get("amount_usd", 0),
                quantity=item.get("quantity", 1),
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

def _sync_asset_valuation_history(asset, items):
    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES and asset.asset_type not in VEHICLE_ASSET_TYPES and asset.asset_type not in OTHER_ASSET_TYPES:
        AssetValuationHistory.objects.filter(asset=asset).delete()
        return

    AssetValuationHistory.objects.filter(asset=asset).delete()
    created_items = []
    for item in items or []:
        if not item.get("valuation_date"):
            continue
        created_items.append(
            AssetValuationHistory.objects.create(
                asset=asset,
                valuation_date=item.get("valuation_date"),
                market_value=item.get("market_value", 0),
                valuation_source=item.get("valuation_source", "Manual"),
                notes=item.get("notes", ""),
            )
        )

    if created_items:
        latest_item = max(created_items, key=lambda value: value.valuation_date)
        asset.current_market_value = latest_item.market_value
        asset.last_valuation_date = latest_item.valuation_date
        asset.valuation_source = latest_item.valuation_source
        asset.save()

