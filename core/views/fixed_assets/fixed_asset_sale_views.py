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
    AssetSale,

)
import datetime
from core.utils import _to_decimal

from core.services.fixed_assets.asset_sale_service import _resolve_sale_deposit_values, _sale_payment_row
from core.services.fixed_assets.asset_purchase_service import _apply_asset_balance_delta
from core.services.fixed_assets.gold_sync_service import _sync_gold_balance_from_assets


@method_decorator(csrf_exempt, name="dispatch")
class AssetSaleView(View):

    def get(self, request, asset_id):
        asset = get_object_or_404(FixedAsset, pk=asset_id)

        if hasattr(asset, "sale"):
            return JsonResponse(asset.sale.to_dict())

        return JsonResponse({}, status=404)

    def post(self, request, asset_id):
        asset = get_object_or_404(FixedAsset, pk=asset_id)

        data = json.loads(request.body)
        sale_date_value = data.get("sale_date")
        if isinstance(sale_date_value, str):
            try:
                sale_date_value = datetime.date.fromisoformat(sale_date_value)
            except ValueError:
                pass

        existing_sale = getattr(asset, "sale", None)

        try:
            with transaction.atomic():
                if existing_sale is not None:
                    previous_row = _sale_payment_row(existing_sale)
                    _apply_asset_balance_delta(
                        currency_id=previous_row["currency_id"],
                        payment_method=previous_row["payment_method"],
                        bank_id=previous_row["bank_id"],
                        amount_delta=-_to_decimal(previous_row["amount"]),
                    )

                deposit_values = _resolve_sale_deposit_values(data, existing_sale=existing_sale)

                sale, created = AssetSale.objects.update_or_create(
                    asset=asset,
                    defaults={
                        "sale_date": sale_date_value,
                        "sale_price": data["sale_price"],
                        "selling_expenses": data.get("selling_expenses", 0),
                        "net_sale_amount": data["net_sale_amount"],
                        "deposit_balance_id": data.get("deposit_balance_id"),
                        "deposit_currency_id": deposit_values["deposit_currency_id"],
                        "deposit_method": deposit_values["deposit_method"],
                        "deposit_bank_id": deposit_values["deposit_bank_id"],
                        "notes": data.get("notes", ""),
                    },
                )

                current_row = _sale_payment_row(sale)
                _apply_asset_balance_delta(
                    currency_id=current_row["currency_id"],
                    payment_method=current_row["payment_method"],
                    bank_id=current_row["bank_id"],
                    amount_delta=_to_decimal(current_row["amount"]),
                )

                asset.status = "Sold"
                asset.save()
                _sync_gold_balance_from_assets()

        except ValueError as exc:
            return JsonResponse(
                {
                    "error": str(exc),
                    "error_key": str(exc),
                },
                status=400,
            )

        return JsonResponse(sale.to_dict(), status=201 if created else 200)

    def delete(self, request, asset_id):
        asset = get_object_or_404(FixedAsset, pk=asset_id)

        if not hasattr(asset, "sale"):
            return JsonResponse({}, status=404)

        try:
            with transaction.atomic():
                sale_row = _sale_payment_row(asset.sale)
                _apply_asset_balance_delta(
                    currency_id=sale_row["currency_id"],
                    payment_method=sale_row["payment_method"],
                    bank_id=sale_row["bank_id"],
                    amount_delta=-_to_decimal(sale_row["amount"]),
                )

                asset.sale.delete()

                if asset.status == "Sold":
                    asset.status = "Owned"
                    asset.save()

                _sync_gold_balance_from_assets()

        except ValueError as exc:
            return JsonResponse(
                {
                    "error": str(exc),
                    "error_key": str(exc),
                },
                status=400,
            )

        return JsonResponse({"deleted": True})


