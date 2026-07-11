# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

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
    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES:
        AssetFurniture.objects.filter(asset=asset).delete()
        return

    AssetFurniture.objects.filter(asset=asset).delete()
    for item in items or []:
        if not item.get("name"):
            continue
        AssetFurniture.objects.create(
            asset=asset,
            name=item.get("name", ""),
            category=item.get("category", ""),
            purchase_date=item.get("purchase_date") or None,
            amount_egp=item.get("amount_egp", 0),
            usd_rate=item.get("usd_rate", 0),
            amount_usd=item.get("amount_usd", 0),
            quantity=item.get("quantity", 1),
            notes=item.get("notes", ""),
        )


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


