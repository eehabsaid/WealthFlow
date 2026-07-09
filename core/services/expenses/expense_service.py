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


def _get_target_cash_balance_entry(payment_method, bank_id):
    qs = BalanceEntry.objects.select_for_update().filter(
        balance_type=BalanceEntry.BalanceType.CASH,
    )
    egp_or_cash_qs = qs.filter(
        Q(currency__code__iexact="EGP")
        | Q(currency__code__iexact="CASH")
        | Q(currency__name__iexact="Cash")
    )
    if egp_or_cash_qs.exists():
        qs = egp_or_cash_qs

    normalized_method = _normalize_expense_payment_method(payment_method)
    if normalized_method == "cash":
        qs = qs.filter(bank__isnull=True)
    else:
        qs = qs.filter(bank_id=bank_id)

    return qs.order_by("id").first()


def _apply_expense_balance_delta(payment_method, bank_id, amount_delta):
    if not _expense_affects_balance(payment_method):
        return

    delta = Decimal(str(amount_delta or 0))
    if delta == 0:
        return

    entry = _get_target_cash_balance_entry(payment_method, bank_id)
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
            if _expense_affects_balance(payment_method):
                target_entry = _get_target_cash_balance_entry(payment_method, bank_id)
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
                currency_id=data.get("currency_id"),
                bank_id=bank_id,
                payment_method=payment_method,
                notes=data.get("notes", ""),
            )
            _apply_expense_balance_delta(exp.payment_method, exp.bank_id, -exp.amount)
            return exp

    @staticmethod
    def update_expense(expense_id, data):
        with transaction.atomic():
            from django.shortcuts import get_object_or_404
            exp = get_object_or_404(Expense, pk=expense_id)

            previous_amount = Decimal(exp.amount or 0)
            previous_method = exp.payment_method
            previous_bank_id = exp.bank_id

            if "date" in data:
                from datetime import date as _date
                d = _date.fromisoformat(data["date"])
                exp.date = d
                exp.year = d.year
                exp.month = d.month

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
                    setattr(exp, f, data[f])

            if _normalize_expense_payment_method(exp.payment_method) == "cash":
                exp.bank_id = None

            next_amount = Decimal(exp.amount or 0)
            if _expense_affects_balance(exp.payment_method):
                next_target = _get_target_cash_balance_entry(exp.payment_method, exp.bank_id)
                if not next_target:
                    raise ValueError("matching_balance_entry_not_found")

                available_balance = Decimal(next_target.amount or 0)
                if _expense_affects_balance(previous_method):
                    previous_target = _get_target_cash_balance_entry(previous_method, previous_bank_id)
                    if previous_target and previous_target.id == next_target.id:
                        available_balance += previous_amount

                if next_amount > available_balance:
                    raise ValueError("insufficient_balance")

            _apply_expense_balance_delta(previous_method, previous_bank_id, previous_amount)
            exp.save()
            _apply_expense_balance_delta(exp.payment_method, exp.bank_id, -Decimal(exp.amount or 0))
            return exp

    @staticmethod
    def delete_expense(expense_id):
        with transaction.atomic():
            from django.shortcuts import get_object_or_404
            exp = get_object_or_404(Expense, pk=expense_id)
            _apply_expense_balance_delta(exp.payment_method, exp.bank_id, Decimal(exp.amount or 0))
            exp.delete()
