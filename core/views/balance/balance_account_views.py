from core.views.certificate_views import _run_certificate_interest_sync
# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import (
    BalanceEntry,
    GoldPuritySetting,

)

from core.services.balance.net_worth_service import NetWorthService

User = get_user_model()
from core.utils import (
    _normalize_gold_purity,
)

if not __name__.endswith('.auth_views') and not __name__ == 'core.views.auth_views':
    try:
        pass
    except (ImportError, ValueError):
        pass

@method_decorator(csrf_exempt, name="dispatch")
class BalanceListView(View):
    def _normalize_purity_key(self, purity_value):
        text = str(purity_value or "").strip().lower()
        if "24" in text or "999" in text:
            return "24k"
        if "22" in text or "916" in text:
            return "22k"
        if "21" in text or "875" in text:
            return "21k"
        if "18" in text or "750" in text:
            return "18k"
        return "24k"

    def _cashback_per_gram_for_purity(self, purity_value):
        key = self._normalize_purity_key(purity_value)
        setting = GoldPuritySetting.objects.filter(key=key, is_active=True).first()
        return float(setting.cashback_per_gram) if setting else 0.0

    def _sell_per_gram_for_purity(self, latest_gold, purity_value):
        if not latest_gold:
            return 0.0
        key = self._normalize_purity_key(purity_value)
        if key == "22k":
            return float(latest_gold.carat_22k or 0)
        if key == "21k":
            return float(latest_gold.carat_21k or 0)
        if key == "18k":
            return float(latest_gold.carat_18k or 0)
        return float(latest_gold.carat_24k or 0)

    def get(self, request):
        _run_certificate_interest_sync()
        return JsonResponse(NetWorthService().balance_payload())

    def post(self, request):
        data = json.loads(request.body) if request.body else {}
        balance_type = data.get("balance_type")
        title = data.get("title")
        if not balance_type or not title:
            return JsonResponse({"error": "balance_type and title are required"}, status=400)

        purity = data.get("purity", "")
        if balance_type == BalanceEntry.BalanceType.GOLD:
            purity = _normalize_gold_purity(purity)
        else:
            purity = ""

        entry = BalanceEntry.objects.create(
            title=title,
            balance_type=balance_type,
            bank_id=data.get("bank_id"),
            currency_id=data.get("currency_id", 1),
            purity=purity,
            amount=data.get("amount", 0),
            notes=data.get("notes", ""),
        )
        return JsonResponse(entry.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class BalanceDetailView(View):
    def put(self, request, pk):
        entry = get_object_or_404(BalanceEntry, pk=pk)
        data = json.loads(request.body)
        for field in [
            "title",
            "balance_type",
            "bank_id",
            "currency_id",
            "amount",
            "notes",
            "purity",
        ]:
            if field in data:
                setattr(entry, field, data[field])

        if entry.balance_type == BalanceEntry.BalanceType.GOLD:
            entry.purity = _normalize_gold_purity(entry.purity)
        else:
            entry.purity = ""

        entry.save()
        return JsonResponse(entry.to_dict())

    def delete(self, request, pk):
        entry = get_object_or_404(BalanceEntry, pk=pk)
        entry.delete()
        return JsonResponse({"deleted": pk})