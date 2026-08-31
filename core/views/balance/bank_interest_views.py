import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db import transaction
from core.models import BankInterest


@method_decorator(csrf_exempt, name="dispatch")
class BankInterestListView(View):
    def get(self, request):
        entries = BankInterest.objects.select_related("bank", "currency").all()
        return JsonResponse({"bank_interests": [e.to_dict() for e in entries]})

    def post(self, request):
        try:
            data = json.loads(request.body)
            interest_date = data["interest_date"]
            bank_id = data.get("bank_id")
            currency_id = data["currency_id"]
            amount = float(data.get("amount", 0))
            notes = data.get("notes", "")

            with transaction.atomic():
                entry = BankInterest.objects.create(
                    interest_date=interest_date,
                    bank_id=bank_id,
                    currency_id=currency_id,
                    amount=amount,
                    notes=notes,
                )
                entry.apply_interest()

            return JsonResponse(entry.to_dict(), status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@method_decorator(csrf_exempt, name="dispatch")
class BankInterestDetailView(View):
    def put(self, request, pk):
        try:
            entry = get_object_or_404(BankInterest, pk=pk)
            data = json.loads(request.body)

            with transaction.atomic():
                # Reverse the old interest credit
                entry.reverse_interest()

                if "interest_date" in data:
                    entry.interest_date = data["interest_date"]
                if "bank_id" in data:
                    entry.bank_id = data["bank_id"] if data["bank_id"] else None
                if "currency_id" in data:
                    entry.currency_id = data["currency_id"]
                if "amount" in data:
                    entry.amount = float(data["amount"])
                if "notes" in data:
                    entry.notes = data["notes"]

                entry.save()

                # Re-apply with the updated values
                entry.apply_interest()

            return JsonResponse(entry.to_dict())
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def delete(self, request, pk):
        try:
            entry = get_object_or_404(BankInterest, pk=pk)
            with transaction.atomic():
                entry.reverse_interest()
                entry.delete()
            return JsonResponse({"deleted": pk})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
