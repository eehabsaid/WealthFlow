"""API: rent received (settles a month of a rental's virtual income). Owner-scoped."""

import json

from django.http import JsonResponse
from django.utils import timezone
from django.views import View

from core.models import AssetRental, RentReceipt
from core.services.fixed_assets.rent_receipt_service import RentReceiptError, delete_receipt, month_start, record_receipt
from core.validators import _api_auth_required
from core.validators.json_body import parse_json_body


def _rental_or_none(request, asset_id):
    return AssetRental.objects.select_related("asset", "bank").filter(asset_id=asset_id, asset__owner=request.user).first()


class RentReceiptListView(View):
    def get(self, request, asset_id):
        err = _api_auth_required(request)
        if err:
            return err
        rental = _rental_or_none(request, asset_id)
        if rental is None:
            return JsonResponse({"error": "Rental not found"}, status=404)
        receipts = RentReceipt.objects.select_related("rental", "bank", "currency").filter(rental=rental)
        current = month_start(timezone.localdate())
        return JsonResponse({
            "receipts": [r.to_dict() for r in receipts],
            "current_period": current.strftime("%Y-%m"),
            "current_month_settled": any(r.period_start == current for r in receipts),
        })

    def post(self, request, asset_id):
        err = _api_auth_required(request)
        if err:
            return err
        rental = _rental_or_none(request, asset_id)
        if rental is None:
            return JsonResponse({"error": "Rental not found"}, status=404)
        try:
            data = parse_json_body(request)
            receipt = record_receipt(
                request.user, rental, period=data.get("period"), amount=data.get("amount"),
                received_date=data.get("received_date") or None, notes=str(data.get("notes") or "")[:500],
            )
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)
        except RentReceiptError as exc:
            return JsonResponse({"error": str(exc)}, status=exc.status)
        except ValueError:
            return JsonResponse({"error": "Invalid date."}, status=400)
        return JsonResponse(receipt.to_dict(), status=201)


class RentReceiptDetailView(View):
    def delete(self, request, pk):
        err = _api_auth_required(request)
        if err:
            return err
        receipt = RentReceipt.objects.select_related("rental", "bank", "currency").filter(pk=pk, owner=request.user).first()
        if receipt is None:
            return JsonResponse({"error": "Receipt not found"}, status=404)
        delete_receipt(receipt)
        return JsonResponse({"ok": True})
