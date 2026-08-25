# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from decimal import Decimal
from django.db import transaction
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import (
    AssetFurniture,

)
from core.services.expenses.expense_service import _apply_expense_balance_delta


def _balance_error_response(exc):
    """Mirrors the error_key mapping used by core/views/expense_views.py so the
    frontend's existing bank_account_required / insufficient_balance handling
    works identically for fixed-asset money-movement endpoints."""
    key = str(exc)
    messages = {
        "bank_account_required": "Bank account is required for this payment method",
        "matching_balance_entry_not_found": "Matching balance entry not found",
        "insufficient_balance": "insufficient_balance",
    }
    if key in messages:
        return JsonResponse({"error": messages[key], "error_key": key}, status=400)
    raise exc

@method_decorator(csrf_exempt, name="dispatch")
class AssetFurnitureListView(View):

    def get(self, request):
        asset_id = request.GET.get("asset")

        qs = AssetFurniture.objects.all().order_by("name")

        if asset_id:
            qs = qs.filter(asset_id=asset_id)

        return JsonResponse({
            "furniture": [f.to_dict() for f in qs]
        })

    def post(self, request):
        data = json.loads(request.body)

        payment_method = data.get("payment_method", "Cash")
        bank_id = data.get("bank_id")
        amount_egp = data.get("amount_egp", 0)

        try:
            with transaction.atomic():
                item = AssetFurniture.objects.create(
                    asset_id=data["asset_id"],
                    name=data["name"],
                    category=data.get("category", ""),
                    purchase_date=data.get("purchase_date") or None,
                    amount_egp=amount_egp,
                    usd_rate=data.get("usd_rate", 0),
                    amount_usd=data.get("amount_usd", 0),
                    quantity=data.get("quantity", 1),
                    payment_method=payment_method,
                    bank_id=bank_id,
                    notes=data.get("notes", ""),
                )
                _apply_expense_balance_delta(
                    payment_method,
                    bank_id,
                    -Decimal(str(amount_egp or 0)),
                )
        except ValueError as exc:
            return _balance_error_response(exc)

        return JsonResponse(item.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class AssetFurnitureDetailView(View):

    def put(self, request, pk):
        item = get_object_or_404(AssetFurniture, pk=pk)

        data = json.loads(request.body)

        old_payment_method = item.payment_method
        old_bank_id = item.bank_id
        old_amount_egp = item.amount_egp

        fields = [
            "name",
            "category",
            "purchase_date",
            "amount_egp",
            "usd_rate",
            "amount_usd",
            "quantity",
            "payment_method",
            "bank_id",
            "notes",
        ]

        for field in fields:
            if field in data:
                setattr(item, field, data[field])

        try:
            with transaction.atomic():
                item.save()
                _apply_expense_balance_delta(
                    old_payment_method,
                    old_bank_id,
                    Decimal(str(old_amount_egp or 0)),
                )
                _apply_expense_balance_delta(
                    item.payment_method,
                    item.bank_id,
                    -Decimal(str(item.amount_egp or 0)),
                )
        except ValueError as exc:
            return _balance_error_response(exc)

        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        item = get_object_or_404(AssetFurniture, pk=pk)

        try:
            with transaction.atomic():
                _apply_expense_balance_delta(
                    item.payment_method,
                    item.bank_id,
                    Decimal(str(item.amount_egp or 0)),
                )
                item.delete()
        except ValueError as exc:
            return _balance_error_response(exc)

        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
class AssetFurnitureCategoriesView(View):
    def get(self, request):
        from core.constants import FURNITURE_CATEGORIES
        return JsonResponse({"categories": FURNITURE_CATEGORIES})
