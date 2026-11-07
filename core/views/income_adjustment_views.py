# pyright: reportMissingTypeStubs=false, reportUnknownParameterType=false, reportMissingParameterType=false

from decimal import Decimal, InvalidOperation

from django.http import JsonResponse
from django.views import View

from core.models import MonthlyIncomeAdjustment
from core.validators import _api_auth_required
from core.validators.json_body import parse_json_body


def _period_or_error(year, month):
    try:
        year, month = int(year), int(month)
    except (TypeError, ValueError):
        return None, JsonResponse({"error": "year and month are required"}, status=400)
    if not (1900 <= year <= 2200 and 1 <= month <= 12):
        return None, JsonResponse({"error": "invalid year or month"}, status=400)
    return (year, month), None


class MonthlyIncomeAdjustmentView(View):
    """Manual extra income for one owner + year + month (GET reads it, PUT saves it)."""

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        period, err = _period_or_error(request.GET.get("year"), request.GET.get("month"))
        if err:
            return err
        row = MonthlyIncomeAdjustment.objects.filter(owner=request.user, year=period[0], month=period[1]).first()
        return JsonResponse({"year": period[0], "month": period[1], "amount": float(row.amount) if row else 0.0})

    def put(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        data = parse_json_body(request)
        period, err = _period_or_error(data.get("year"), data.get("month"))
        if err:
            return err
        try:
            amount = Decimal(str(data.get("amount", 0))).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            return JsonResponse({"error": "amount must be a number"}, status=400)
        if not amount.is_finite() or amount < 0 or amount >= Decimal("10") ** 12:
            return JsonResponse({"error": "amount out of range"}, status=400)
        row, _ = MonthlyIncomeAdjustment.objects.update_or_create(
            owner=request.user, year=period[0], month=period[1], defaults={"amount": amount}
        )
        return JsonResponse(row.to_dict())
