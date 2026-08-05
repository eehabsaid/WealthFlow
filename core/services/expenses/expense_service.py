from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from core.models import Expense, BalanceEntry

def _normalize_expense_payment_method(method_value):
    method = str(method_value or "").strip().lower()
    if method == "cash":
        return "cash"
    if method in {"bank", "bank transfer", "bank_transfer"}:
        return "bank"
    if method == "card":
        return "card"
    return method

def _expense_requires_bank(method_value):
    return _normalize_expense_payment_method(method_value) in {"bank", "card"}

def _expense_affects_balance(method_value):
    return _normalize_expense_payment_method(method_value) in {"cash", "bank", "card"}

def _get_target_cash_balance_entry(payment_method, bank_id, currency_id=None):
    qs = BalanceEntry.objects.select_for_update().filter(
        balance_type=BalanceEntry.BalanceType.CASH,
    )
    if currency_id:
        qs = qs.filter(currency_id=currency_id)
    else:
        egp_or_cash_qs = qs.filter(
            Q(currency__code__iexact="EGP")
            | Q(currency__code__iexact="CASH")
            | Q(currency__name__iexact="Cash")
        )
        if egp_or_cash_qs.exists():
            qs = qs.filter(id__in=egp_or_cash_qs.values_list('id', flat=True))

    normalized_method = _normalize_expense_payment_method(payment_method)
    if normalized_method == "cash":
        qs = qs.filter(bank__isnull=True)
    else:
        qs = qs.filter(bank_id=bank_id)

    return qs.order_by("id").first()

def _apply_expense_balance_delta(payment_method, bank_id, amount_delta, currency_id=None):
    if not _expense_affects_balance(payment_method):
        return

    delta = Decimal(str(amount_delta or 0))
    if delta == 0:
        return

    entry = _get_target_cash_balance_entry(payment_method, bank_id, currency_id)
    if not entry:
        raise ValueError("matching_balance_entry_not_found")

    if delta < 0 and (Decimal(entry.amount or 0) + delta) < 0:
        raise ValueError("insufficient_balance")

    entry.amount = Decimal(entry.amount or 0) + delta
    entry.save(update_fields=["amount"])

class ExpenseService(object):
    @staticmethod
    def create_expense(data):
        from datetime import date as _date

        payment_method = data.get("payment_method", "Cash")
        bank_id = data.get("bank_id")
        if _expense_requires_bank(payment_method) and not bank_id:
            raise ValueError("bank_account_required")
        
        if _normalize_expense_payment_method(payment_method) == "cash":
            bank_id = None

        d = _date.fromisoformat(data["date"])
        with transaction.atomic():
            amount_value = Decimal(str(data.get("amount", 0) or 0))

            exchange_rate_val = Decimal("1")
            currency_id = data.get("currency_id")
            if currency_id:
                from core.models import Currency, ExchangeRate
                from core.services.shared.currency_conversion_service import CurrencyConversionService
                try:
                    curr = Currency.objects.get(id=currency_id)
                    if curr.code.upper() != "EGP":
                        has_rate = ExchangeRate.objects.filter(
                            currency_code__iexact=curr.code,
                            fetched_at__date__lte=d
                        ).exists()
                        if not has_rate:
                            raise ValueError("exchange_rate_missing")
                        exchange_rate_val = CurrencyConversionService.get_latest_buy_rate(curr.code, target_date=d)
                except Currency.DoesNotExist:
                    pass
            amount_egp_val = amount_value * exchange_rate_val

            if _expense_affects_balance(payment_method):
                target_entry = _get_target_cash_balance_entry(payment_method, bank_id, currency_id)
                if not target_entry:
                    raise ValueError("matching_balance_entry_not_found")
                if amount_value > Decimal(target_entry.amount or 0):
                    raise ValueError("insufficient_balance")

            exp = Expense.objects.create(
                date=d,
                year=d.year,
                month=d.month,
                category_id=data.get("category_id"),
                subcategory_id=data.get("subcategory_id"),
                description=data.get("description", ""),
                amount=amount_value,
                exchange_rate=exchange_rate_val,
                amount_egp=amount_egp_val,
                currency_id=currency_id,
                bank_id=bank_id,
                payment_method=payment_method,
                notes=data.get("notes", ""),
            )
            _apply_expense_balance_delta(exp.payment_method, exp.bank_id, -exp.amount, exp.currency_id)
            return exp

    @staticmethod
    def update_expense(expense_id, data):
        with transaction.atomic():
            from django.shortcuts import get_object_or_404
            exp = get_object_or_404(Expense, pk=expense_id)

            previous_amount = Decimal(exp.amount or 0)
            previous_method = exp.payment_method
            previous_bank_id = exp.bank_id
            previous_currency_id = exp.currency_id

            recalc_needed = False
            if "date" in data:
                from datetime import date as _date
                d = _date.fromisoformat(data["date"])
                if exp.date != d:
                    exp.date = d
                    exp.year = d.year
                    exp.month = d.month
                    recalc_needed = True

            next_method = data.get("payment_method", exp.payment_method)
            next_bank_id = data.get("bank_id", exp.bank_id)
            if _expense_requires_bank(next_method) and not next_bank_id:
                raise ValueError("bank_account_required")

            for f in [
                "category_id",
                "subcategory_id",
                "description",
                "amount",
                "currency_id",
                "bank_id",
                "payment_method",
                "notes",
            ]:
                if f in data:
                    if getattr(exp, f) != data[f]:
                        setattr(exp, f, data[f])
                        if f in ["amount", "currency_id"]:
                            recalc_needed = True

            if recalc_needed:
                exchange_rate_val = Decimal("1")
                if exp.currency_id:
                    from core.models import Currency, ExchangeRate
                    from core.services.shared.currency_conversion_service import CurrencyConversionService
                    try:
                        curr = Currency.objects.get(id=exp.currency_id)
                        if curr.code.upper() != "EGP":
                            has_rate = ExchangeRate.objects.filter(
                                currency_code__iexact=curr.code,
                                fetched_at__date__lte=exp.date
                            ).exists()
                            if not has_rate:
                                raise ValueError("exchange_rate_missing")
                            exchange_rate_val = CurrencyConversionService.get_latest_buy_rate(curr.code, target_date=exp.date)
                    except Currency.DoesNotExist:
                        pass
                exp.exchange_rate = exchange_rate_val
                exp.amount_egp = Decimal(str(exp.amount or 0)) * exchange_rate_val

            if _normalize_expense_payment_method(exp.payment_method) == "cash":
                exp.bank_id = None

            next_amount = Decimal(exp.amount or 0)
            if _expense_affects_balance(exp.payment_method):
                next_target = _get_target_cash_balance_entry(exp.payment_method, exp.bank_id, exp.currency_id)
                if not next_target:
                    raise ValueError("matching_balance_entry_not_found")

                available_balance = Decimal(next_target.amount or 0)
                if _expense_affects_balance(previous_method):
                    previous_target = _get_target_cash_balance_entry(previous_method, previous_bank_id, previous_currency_id)
                    if previous_target and previous_target.id == next_target.id:
                        available_balance += previous_amount

                if next_amount > available_balance:
                    raise ValueError("insufficient_balance")

            _apply_expense_balance_delta(previous_method, previous_bank_id, previous_amount, previous_currency_id)
            exp.save()
            _apply_expense_balance_delta(exp.payment_method, exp.bank_id, -Decimal(exp.amount or 0), exp.currency_id)
            return exp

    @staticmethod
    def delete_expense(expense_id):
        with transaction.atomic():
            from django.shortcuts import get_object_or_404
            exp = get_object_or_404(Expense, pk=expense_id)
            _apply_expense_balance_delta(exp.payment_method, exp.bank_id, Decimal(exp.amount or 0), exp.currency_id)
            exp.delete()
