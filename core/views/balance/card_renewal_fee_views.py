import json
from decimal import Decimal
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db import transaction
from core.models import CardRenewalFee


def _balance_error_response(exc):
    """Mirrors the error_key mapping used by credit_card_payment_views.py
    / expense_views.py, so the frontend's existing insufficient_balance
    handling works identically here."""
    key = str(exc)
    messages = {
        "bank_account_required": "Bank account is required for this fee",
        "matching_balance_entry_not_found": "Matching balance entry not found",
        "insufficient_balance": "insufficient_balance",
    }
    if key in messages:
        return JsonResponse({"error": messages[key], "error_key": key}, status=400)
    raise exc


@method_decorator(csrf_exempt, name="dispatch")
class CardRenewalFeeListView(View):
    def get(self, request):
        entries = CardRenewalFee.objects.select_related("bank").all()
        return JsonResponse({"card_renewal_fees": [e.to_dict() for e in entries]})

    def post(self, request):
        try:
            data = json.loads(request.body)
            fee_date = data["fee_date"]
            bank_id = data["bank_id"]
            card_label = data.get("card_label", "")
            amount_egp = Decimal(str(data.get("amount_egp", 0) or 0))
            notes = data.get("notes", "")

            with transaction.atomic():
                entry = CardRenewalFee.objects.create(
                    fee_date=fee_date,
                    bank_id=bank_id,
                    card_label=card_label,
                    amount_egp=amount_egp,
                    notes=notes,
                )
                entry.apply_and_mirror()

            return JsonResponse(entry.to_dict(), status=201)
        except ValueError as exc:
            return _balance_error_response(exc)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@method_decorator(csrf_exempt, name="dispatch")
class CardRenewalFeeDetailView(View):
    def put(self, request, pk):
        entry = get_object_or_404(CardRenewalFee, pk=pk)
        try:
            data = json.loads(request.body)

            with transaction.atomic():
                # Reverse the old debit + mirror before applying new values,
                # same discipline as CreditCardPayment / BankInterest saves.
                entry.reverse_and_unmirror()

                if "fee_date" in data:
                    entry.fee_date = data["fee_date"]
                if "bank_id" in data:
                    entry.bank_id = data["bank_id"]
                if "card_label" in data:
                    entry.card_label = data["card_label"]
                if "amount_egp" in data:
                    entry.amount_egp = Decimal(str(data["amount_egp"] or 0))
                if "notes" in data:
                    entry.notes = data["notes"]

                entry.save()
                entry.apply_and_mirror()

            return JsonResponse(entry.to_dict())
        except ValueError as exc:
            return _balance_error_response(exc)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def delete(self, request, pk):
        entry = get_object_or_404(CardRenewalFee, pk=pk)
        try:
            with transaction.atomic():
                entry.reverse_and_unmirror()
                entry.delete()
            return JsonResponse({"deleted": pk})
        except ValueError as exc:
            return _balance_error_response(exc)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
