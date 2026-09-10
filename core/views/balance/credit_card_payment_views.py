import json
from decimal import Decimal
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db import transaction
from core.models import CreditCardPayment, Bank
from core.validators import _api_auth_required, _owned_object_or_404


def _balance_error_response(exc):
    """Mirrors the error_key mapping used by expense_views.py / the
    fixed-asset money-movement endpoints, so the frontend's existing
    insufficient_balance handling works identically here."""
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
class CreditCardPaymentListView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        entries = CreditCardPayment.objects.select_related("bank").filter(owner=request.user)
        return JsonResponse({"credit_card_payments": [e.to_dict() for e in entries]})

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            data = json.loads(request.body)
            payment_date = data["payment_date"]
            bank_id = data["bank_id"]
            get_object_or_404(Bank, pk=bank_id, owner=request.user)
            payment_method = data.get("payment_method", "Card")
            card_label = data.get("card_label", "")
            amount_egp = Decimal(str(data.get("amount_egp", 0) or 0))
            notes = data.get("notes", "")

            with transaction.atomic():
                entry = CreditCardPayment.objects.create(
                    owner=request.user,
                    payment_date=payment_date,
                    bank_id=bank_id,
                    payment_method=payment_method,
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
class CreditCardPaymentDetailView(View):
    def put(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        entry = _owned_object_or_404(CreditCardPayment, pk, request)
        try:
            data = json.loads(request.body)
            if "bank_id" in data and data["bank_id"]:
                get_object_or_404(Bank, pk=data["bank_id"], owner=request.user)

            with transaction.atomic():
                # Reverse the old debit + mirror before applying new values,
                # same discipline as BankInterest / Fixed Asset saves.
                entry.reverse_and_unmirror()

                if "payment_date" in data:
                    entry.payment_date = data["payment_date"]
                if "bank_id" in data:
                    entry.bank_id = data["bank_id"]
                if "payment_method" in data:
                    entry.payment_method = data["payment_method"]
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
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        entry = _owned_object_or_404(CreditCardPayment, pk, request)
        try:
            with transaction.atomic():
                entry.reverse_and_unmirror()
                entry.delete()
            return JsonResponse({"deleted": pk})
        except ValueError as exc:
            return _balance_error_response(exc)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
