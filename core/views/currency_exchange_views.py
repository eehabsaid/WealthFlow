import json
from decimal import Decimal
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db import models, transaction

from core.models import CurrencyExchange, BalanceEntry, Currency
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

@method_decorator(csrf_exempt, name="dispatch")
class CurrencyExchangeListView(View):
    def get(self, request):
        qs = CurrencyExchange.objects.select_related(
            "from_balance", "from_balance__bank", "from_currency",
            "to_balance", "to_balance__bank", "to_currency",
            "user", "reversed_by"
        ).all()

        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        currency_code = request.GET.get("currency")
        balance_id = request.GET.get("balance_id")
        user_param = request.GET.get("user")
        status_param = request.GET.get("status")

        if start_date:
            qs = qs.filter(exchange_date__gte=start_date)
        if end_date:
            qs = qs.filter(exchange_date__lte=end_date)
        if currency_code:
            qs = qs.filter(
                models.Q(from_currency__code__iexact=currency_code) |
                models.Q(to_currency__code__iexact=currency_code)
            )
        if balance_id:
            qs = qs.filter(
                models.Q(from_balance_id=balance_id) |
                models.Q(to_balance_id=balance_id)
            )
        if user_param:
            qs = qs.filter(
                models.Q(user__username__icontains=user_param) |
                models.Q(user_id=user_param if user_param.isdigit() else None)
            )
        if status_param and status_param.upper() != "ALL":
            qs = qs.filter(status=status_param.upper())

        return JsonResponse({"exchanges": [e.to_dict() for e in qs]})

    def post(self, request):
        try:
            data = json.loads(request.body)
            exchange_date = data["exchange_date"]
            from_balance_id = data["from_balance_id"]
            to_balance_id = data["to_balance_id"]
            from_amount = Decimal(str(data.get("from_amount", 0)))
            custom_rate_raw = data.get("exchange_rate", None)
            notes = data.get("notes", "")

            if from_balance_id == to_balance_id:
                return JsonResponse({"error": "same_balance_error"}, status=400)
            if from_amount <= 0:
                return JsonResponse({"error": "invalid_amount_error"}, status=400)

            from_balance = get_object_or_404(BalanceEntry, pk=from_balance_id)
            to_balance = get_object_or_404(BalanceEntry, pk=to_balance_id)

            if from_balance.currency_id == to_balance.currency_id:
                return JsonResponse({"error": "same_currency_error"}, status=400)

            custom_rate = Decimal(str(custom_rate_raw)) if custom_rate_raw and float(custom_rate_raw) > 0 else None
            from_code = from_balance.currency.code if from_balance.currency else "EGP"
            to_code = to_balance.currency.code if to_balance.currency else "EGP"

            applied_rate, to_amount = CurrencyConversionService.convert_amount(
                from_amount, from_code, to_code, custom_rate
            )

            with transaction.atomic():
                exchange = CurrencyExchange.objects.create(
                    exchange_date=exchange_date,
                    from_balance=from_balance,
                    to_balance=to_balance,
                    from_currency=from_balance.currency,
                    to_currency=to_balance.currency,
                    from_amount=from_amount,
                    to_amount=to_amount,
                    exchange_rate=applied_rate,
                    notes=notes,
                    user=request.user if hasattr(request, "user") and request.user.is_authenticated else None
                )
                exchange.apply_exchange()

            return JsonResponse(exchange.to_dict(), status=201)
        except ValueError as ve:
            return JsonResponse({"error": str(ve)}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@method_decorator(csrf_exempt, name="dispatch")
class CurrencyExchangeDetailView(View):
    def put(self, request, pk):
        try:
            exchange = get_object_or_404(CurrencyExchange, pk=pk)
            if exchange.status == CurrencyExchange.Status.REVERSED:
                return JsonResponse({"error": "cannot_edit_reversed_error"}, status=400)

            data = json.loads(request.body)
            exchange_date = data.get("exchange_date", str(exchange.exchange_date))
            from_balance_id = data.get("from_balance_id", exchange.from_balance_id)
            to_balance_id = data.get("to_balance_id", exchange.to_balance_id)
            from_amount = Decimal(str(data.get("from_amount", exchange.from_amount)))
            custom_rate_raw = data.get("exchange_rate", exchange.exchange_rate)
            notes = data.get("notes", exchange.notes)

            if from_balance_id == to_balance_id:
                return JsonResponse({"error": "same_balance_error"}, status=400)
            if from_amount <= 0:
                return JsonResponse({"error": "invalid_amount_error"}, status=400)

            from_balance = get_object_or_404(BalanceEntry, pk=from_balance_id)
            to_balance = get_object_or_404(BalanceEntry, pk=to_balance_id)

            custom_rate = Decimal(str(custom_rate_raw)) if custom_rate_raw and float(custom_rate_raw) > 0 else None
            from_code = from_balance.currency.code if from_balance.currency else "EGP"
            to_code = to_balance.currency.code if to_balance.currency else "EGP"

            applied_rate, to_amount = CurrencyConversionService.convert_amount(
                from_amount, from_code, to_code, custom_rate
            )

            with transaction.atomic():
                # Step 1: Reverse original transaction
                exchange.reverse_exchange(user=request.user if hasattr(request, "user") and request.user.is_authenticated else None, is_edit=True)

                # Step 2: Apply updated parameters
                exchange.exchange_date = exchange_date
                exchange.from_balance = from_balance
                exchange.to_balance = to_balance
                exchange.from_currency = from_balance.currency
                exchange.to_currency = to_balance.currency
                exchange.from_amount = from_amount
                exchange.to_amount = to_amount
                exchange.exchange_rate = applied_rate
                exchange.notes = notes
                
                # Step 3: Apply updated transaction
                exchange.apply_exchange()

            return JsonResponse(exchange.to_dict())
        except ValueError as ve:
            return JsonResponse({"error": str(ve)}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def delete(self, request, pk):
        try:
            exchange = get_object_or_404(CurrencyExchange, pk=pk)
            with transaction.atomic():
                exchange.reverse_exchange(user=request.user if hasattr(request, "user") and request.user.is_authenticated else None, is_edit=False)
            return JsonResponse({"reversed": pk, "status": "REVERSED", "exchange": exchange.to_dict()})
        except ValueError as ve:
            return JsonResponse({"error": str(ve)}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
