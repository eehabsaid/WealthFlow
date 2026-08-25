# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from core.models import (
    Bank,
    BalanceEntry,

)

User = get_user_model()

@method_decorator(csrf_exempt, name="dispatch")
class BankListView(View):
    def get(self, request):
        return JsonResponse({"banks": [b.to_dict() for b in Bank.objects.all()]})

    def post(self, request):
        data = json.loads(request.body)
        from core.services import BankService
        bank = BankService.create_bank(data)
        return JsonResponse(bank.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class BankWithBalanceListView(View):
    """
    Returns only banks that have at least one active, non-Gold/Certificate
    BalanceEntry behind them. Used by money-movement forms (Payment Method +
    Bank selectors) across Expenses and Fixed Assets, so the person can only
    pick a bank that actually has a tracked balance.
    """
    def get(self, request):
        bank_ids = (
            BalanceEntry.objects.exclude(
                balance_type__in=[BalanceEntry.BalanceType.GOLD, BalanceEntry.BalanceType.CERTIFICATE]
            )
            .filter(bank__isnull=False, bank__is_active=True)
            .values_list("bank_id", flat=True)
            .distinct()
        )
        banks = Bank.objects.filter(id__in=bank_ids).order_by("order", "name")
        return JsonResponse({"banks": [b.to_dict() for b in banks]})

@method_decorator(csrf_exempt, name="dispatch")
class BankDetailView(View):
    def put(self, request, pk):
        data = json.loads(request.body)
        from core.services import BankService
        bank = BankService.update_bank(pk, data)
        return JsonResponse(bank.to_dict())

    def delete(self, request, pk):
        from core.services import BankService
        BankService.delete_bank(pk)
        return JsonResponse({"deleted": pk})

