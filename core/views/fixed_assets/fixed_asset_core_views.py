# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from django.shortcuts import get_object_or_404
from core.models import (
    FixedAsset,
    AssetRenovation,
    AssetAcquisitionCost,
    AssetPurchasePayment,
)
from core.services.fixed_assets.asset_purchase_service import _apply_asset_purchase_rows_delta, _normalize_purchase_payments_payload, _purchase_rows_from_instances, _sync_asset_purchase_payments
from core.services.fixed_assets.vehicle_service import _sync_vehicle_details
from core.services.fixed_assets.gold_sync_service import _sync_gold_balance_from_assets, _sync_gold_details
from core.services.fixed_assets.property_service import _sync_asset_mortgage, _sync_asset_rental, _sync_other_asset_details
from core.services.fixed_assets.asset_maintenance_service import _sync_asset_furniture, _sync_asset_insurance, _sync_asset_maintenance, _sync_asset_valuation_history
from core.constants import REAL_ESTATE_ASSET_TYPES
# Re-exported for backward compatibility — other modules import from this path.
from core.views.fixed_assets.fixed_asset_helpers import (
    _clear_non_selected_asset_details,
    _resolve_asset_usd_rate_and_price,
    _sync_real_estate_details_for_update,
)
from core.views.fixed_assets.fixed_asset_list_view import FixedAssetListView

__all__ = [
    "FixedAssetListView",
    "FixedAssetDetailView",
    "_clear_non_selected_asset_details",
    "_resolve_asset_usd_rate_and_price",
    "_sync_real_estate_details_for_update",
]


@method_decorator(csrf_exempt, name="dispatch")
class FixedAssetDetailView(View):

    def get(self, request, pk):
        asset = get_object_or_404(FixedAsset.objects.prefetch_related("acquisition_costs"), pk=pk)
        return JsonResponse(asset.to_dict())

    def put(self, request, pk):
        asset = get_object_or_404(FixedAsset, pk=pk)

        data = json.loads(request.body)
        vehicle_details = data.get("vehicle_details")
        gold_details = data.get("gold_details")
        other_asset_details = data.get("other_asset_details")

        fields = [
            "name",
            "asset_type",
            "status",
            "purchase_date",
            "purchase_price",
            "purchase_usd_rate",
            "purchase_price_usd",
            "current_market_value",
            "valuation_source",
            "last_valuation_date",
            "notes",
        ]

        previous_rows = _purchase_rows_from_instances(
            AssetPurchasePayment.objects.filter(asset=asset).order_by("id")
        )

        purchase_rows_payload_present = "purchase_payments" in data
        purchase_rows_raw = data.get("purchase_payments", [])

        try:
            with transaction.atomic():
                if purchase_rows_payload_present:
                    allow_empty = len(previous_rows) == 0
                    purchase_rows = _normalize_purchase_payments_payload(
                        purchase_rows_raw,
                        data.get("purchase_price", asset.purchase_price),
                        purchase_currency_id=data.get("purchase_currency_id"),
                        allow_empty=allow_empty,
                    )
                else:
                    purchase_rows = previous_rows

                if previous_rows:
                    _apply_asset_purchase_rows_delta(previous_rows, sign=1)

                for field in fields:
                    if field in data:
                        setattr(asset, field, data[field])

                usd_rate, price_usd = _resolve_asset_usd_rate_and_price(
                    data,
                    current_usd_rate=asset.purchase_usd_rate,
                    current_price_usd=asset.purchase_price_usd
                )
                asset.purchase_usd_rate = usd_rate
                asset.purchase_price_usd = price_usd

                asset.save()

                _sync_real_estate_details_for_update(asset, data.get("real_estate_details"))

                _sync_vehicle_details(asset, vehicle_details)
                _sync_gold_details(asset, gold_details)
                _sync_other_asset_details(asset, other_asset_details)

                AssetRenovation.objects.filter(asset=asset).delete()

                for item in data.get("renovations", []):
                    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES:
                        break

                    AssetRenovation.objects.create(
                        asset=asset,
                        date=item.get("date") or None,
                        category=item.get("category", ""),
                        description=item.get("description", ""),
                        amount_egp=item.get("amount_egp", 0),
                        usd_rate=item.get("usd_rate", 0),
                        amount_usd=item.get("amount_usd", 0),
                        notes=item.get("notes", ""),
                    )

                AssetAcquisitionCost.objects.filter(asset=asset).delete()

                for item in data.get("acquisition_costs", []):
                    if asset.asset_type not in REAL_ESTATE_ASSET_TYPES:
                        break

                    AssetAcquisitionCost.objects.create(
                        asset=asset,
                        date=item.get("date") or None,
                        category=item.get("category", ""),
                        description=item.get("description", ""),
                        amount_egp=item.get("amount_egp") or 0,
                        usd_rate=item.get("usd_rate") or 0,
                        amount_usd=item.get("amount_usd") or 0,
                        notes=item.get("notes", ""),
                    )

                _sync_asset_maintenance(asset, data.get("maintenance", []))
                _sync_asset_insurance(asset, data.get("insurance", []))
                _sync_asset_mortgage(asset, data.get("mortgage_details"))
                _sync_asset_rental(asset, data.get("rental_details"))
                _sync_asset_furniture(asset, data.get("furniture", []))
                _sync_asset_valuation_history(asset, data.get("valuation_history", []))
                _clear_non_selected_asset_details(asset)

                if purchase_rows_payload_present:
                    if purchase_rows:
                        _apply_asset_purchase_rows_delta(purchase_rows, sign=-1)
                        _sync_asset_purchase_payments(asset, purchase_rows)
                    else:
                        AssetPurchasePayment.objects.filter(asset=asset).delete()
                elif previous_rows:
                    _apply_asset_purchase_rows_delta(previous_rows, sign=-1)

                _sync_gold_balance_from_assets()

        except ValueError as exc:
            return JsonResponse(
                {
                    "error": str(exc),
                    "error_key": str(exc),
                },
                status=400,
            )

        return JsonResponse(asset.to_dict())

    def delete(self, request, pk):
        asset = get_object_or_404(FixedAsset, pk=pk)

        purchase_rows = _purchase_rows_from_instances(
            AssetPurchasePayment.objects.filter(asset=asset).order_by("id")
        )

        try:
            with transaction.atomic():
                # Reverse only when this asset has explicit payment-source rows.
                if purchase_rows:
                    _apply_asset_purchase_rows_delta(purchase_rows, sign=1)

                asset.delete()
                _sync_gold_balance_from_assets()
        except ValueError as exc:
            return JsonResponse(
                {
                    "error": str(exc),
                    "error_key": str(exc),
                },
                status=400,
            )

        return JsonResponse({"deleted": pk})
