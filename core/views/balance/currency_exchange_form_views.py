import json
from decimal import Decimal
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404

from core.models import BalanceEntry, Currency
from core.services.shared.currency_conversion_service import CurrencyConversionService


@method_decorator(csrf_exempt, name="dispatch")
class CurrencyExchangeFormOptionsView(View):
    """
    Returns options for the Currency Exchange form.
    Excludes Gold and non-monetary balance entries/currencies.
    """
    def get(self, request):
        currencies = Currency.objects.exclude(code__iexact="GOLD").exclude(name__icontains="gold")

        entries = BalanceEntry.objects.select_related("bank", "currency").exclude(
            balance_type__in=[BalanceEntry.BalanceType.GOLD, BalanceEntry.BalanceType.CERTIFICATE]
        ).exclude(
            currency__code__iexact="GOLD"
        )

        return JsonResponse({
            "currencies": [c.to_dict() for c in currencies],
            "balances": [b.to_dict() for b in entries]
        })


@method_decorator(csrf_exempt, name="dispatch")
class CurrencyExchangeCalculateView(View):
    """
    Backend endpoint for live calculation of exchange rate, converted to_amount,
    and available balance based on selected source & destination balances.
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
            from_balance_id = data.get("from_balance_id")
            to_balance_id = data.get("to_balance_id")
            from_amount_raw = data.get("from_amount", 0)
            custom_rate_raw = data.get("exchange_rate", None)

            if not from_balance_id:
                return JsonResponse({"error": "missing_source_balance"}, status=400)

            from_balance = get_object_or_404(BalanceEntry.objects.select_related("currency", "bank"), pk=from_balance_id)

            to_balance = None
            if to_balance_id:
                to_balance = get_object_or_404(BalanceEntry.objects.select_related("currency", "bank"), pk=to_balance_id)

            from_amount = Decimal(str(from_amount_raw or 0))
            custom_rate = Decimal(str(custom_rate_raw)) if custom_rate_raw and float(custom_rate_raw) > 0 else None

            from_code = from_balance.currency.code if from_balance.currency else "EGP"
            to_code = to_balance.currency.code if (to_balance and to_balance.currency) else from_code

            applied_rate, to_amount = CurrencyConversionService.convert_amount(
                from_amount, from_code, to_code, custom_rate
            )

            return JsonResponse({
                "from_balance_id": from_balance.id,
                "from_balance_title": from_balance.title,
                "from_bank_name": from_balance.bank.name if from_balance.bank else "",
                "from_currency_code": from_code,
                "from_currency_symbol": from_balance.currency.symbol if from_balance.currency else "",
                "from_currency_flag": from_balance.currency.flag if from_balance.currency else "💱",
                "available_balance": float(from_balance.amount),
                "to_balance_id": to_balance.id if to_balance else None,
                "to_balance_title": to_balance.title if to_balance else "",
                "to_bank_name": to_balance.bank.name if (to_balance and to_balance.bank) else "",
                "to_currency_code": to_code,
                "to_currency_symbol": to_balance.currency.symbol if (to_balance and to_balance.currency) else "",
                "to_currency_flag": to_balance.currency.flag if (to_balance and to_balance.currency) else "💱",
                "exchange_rate": float(applied_rate),
                "from_amount": float(from_amount),
                "to_amount": float(to_amount),
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
