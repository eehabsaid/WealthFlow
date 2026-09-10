# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from decimal import Decimal
from django.db import transaction
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import AssetAcquisitionCost, FixedAsset
from core.services.expenses.expense_balance_helpers import _apply_expense_balance_delta
from core.validators import _api_auth_required, _child_owned_object_or_404


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
class AssetAcquisitionCostListView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        asset_id = request.GET.get("asset")
        qs = AssetAcquisitionCost.objects.filter(asset__owner=request.user).order_by("-date", "-id")
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        return JsonResponse({
            "acquisition_costs": [r.to_dict() for r in qs]
        })

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        data = json.loads(request.body)
        asset = get_object_or_404(FixedAsset, pk=data["asset_id"], owner=request.user)
        payment_method = data.get("payment_method", "Cash")
        bank_id = data.get("bank_id")
        amount_egp = data.get("amount_egp") or 0

        try:
            with transaction.atomic():
                item = AssetAcquisitionCost.objects.create(
                    asset=asset,
                    date=data.get("date") or None,
                    category=data["category"],
                    description=data.get("description", ""),
                    amount_egp=amount_egp,
                    usd_rate=data.get("usd_rate") or 0,
                    amount_usd=data.get("amount_usd") or 0,
                    payment_method=payment_method,
                    bank_id=bank_id,
                    notes=data.get("notes", ""),
                )
                _apply_expense_balance_delta(
                    payment_method,
                    bank_id,
                    -Decimal(str(amount_egp or 0)),
                    owner=asset.owner,
                )
        except ValueError as exc:
            return _balance_error_response(exc)

        return JsonResponse(item.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class AssetAcquisitionCostDetailView(View):
    def put(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        item = _child_owned_object_or_404(AssetAcquisitionCost, pk, request, parent_field="asset")
        data = json.loads(request.body)

        old_payment_method = item.payment_method
        old_bank_id = item.bank_id
        old_amount_egp = item.amount_egp

        fields = [
            "date",
            "category",
            "description",
            "amount_egp",
            "usd_rate",
            "amount_usd",
            "payment_method",
            "bank_id",
            "notes",
        ]
        for field in fields:
            if field in data:
                val = data[field]
                if field == "date" and not val:
                    val = None
                elif field in ["amount_egp", "amount_usd", "usd_rate"]:
                    val = val or 0
                setattr(item, field, val)

        try:
            with transaction.atomic():
                item.save()
                _apply_expense_balance_delta(
                    old_payment_method,
                    old_bank_id,
                    Decimal(str(old_amount_egp or 0)),
                    owner=item.asset.owner,
                )
                _apply_expense_balance_delta(
                    item.payment_method,
                    item.bank_id,
                    -Decimal(str(item.amount_egp or 0)),
                    owner=item.asset.owner,
                )
        except ValueError as exc:
            return _balance_error_response(exc)

        return JsonResponse(item.to_dict())

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        item = _child_owned_object_or_404(AssetAcquisitionCost, pk, request, parent_field="asset")

        try:
            with transaction.atomic():
                _apply_expense_balance_delta(
                    item.payment_method,
                    item.bank_id,
                    Decimal(str(item.amount_egp or 0)),
                    owner=item.asset.owner,
                )
                item.delete()
        except ValueError as exc:
            return _balance_error_response(exc)

        return JsonResponse({"deleted": pk})

@method_decorator(csrf_exempt, name="dispatch")
class AssetAcquisitionCostCategoriesView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        from core.constants import ACQUISITION_COST_CATEGORIES
        return JsonResponse({"categories": ACQUISITION_COST_CATEGORIES})
