from decimal import Decimal
from django.db.models import Q
from core.models import BalanceEntry

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

def _get_target_cash_balance_entry(payment_method, bank_id, owner, currency_id=None):
    qs = BalanceEntry.objects.select_for_update().filter(
        owner=owner,
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

def _apply_expense_balance_delta(payment_method, bank_id, amount_delta, *, owner, currency_id=None):
    if not _expense_affects_balance(payment_method):
        return

    delta = Decimal(str(amount_delta or 0))
    if delta == 0:
        return

    entry = _get_target_cash_balance_entry(payment_method, bank_id, owner, currency_id)
    if not entry:
        raise ValueError("matching_balance_entry_not_found")

    if delta < 0 and (Decimal(entry.amount or 0) + delta) < 0:
        raise ValueError("insufficient_balance")

    entry.amount = Decimal(entry.amount or 0) + delta
    entry.save(update_fields=["amount"])

