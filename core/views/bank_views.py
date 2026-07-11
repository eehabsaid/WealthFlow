# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from core.models import (
    Bank,

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

