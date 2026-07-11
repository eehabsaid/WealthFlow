# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

from decimal import Decimal
from core.models import (
    BalanceEntry,
    Currency,
    AssetPurchasePayment,

)
from core.constants import (
    ASSET_PAYMENT_METHOD_CASH,
    ASSET_PAYMENT_METHOD_NORMALIZED,
)
from core.utils import (
    _to_decimal,
)


def _normalize_asset_payment_method(method_value):
    normalized = str(method_value or "").strip().lower()
    return ASSET_PAYMENT_METHOD_NORMALIZED.get(normalized, ASSET_PAYMENT_METHOD_CASH)


def _asset_payment_requires_bank(method_value):
    return _normalize_asset_payment_method(method_value) != ASSET_PAYMENT_METHOD_CASH


def _asset_payment_currency_required(currency_id):
    return currency_id is not None and str(currency_id).strip() != ""


def _default_egp_currency_id():
    currency = Currency.objects.filter(code__iexact="EGP").order_by("id").first()
    return currency.id if currency else None


def _normalize_purchase_payments_payload(rows, purchase_price, purchase_currency_id=None, allow_empty=False):
    normalized_rows = []
    running_total = Decimal("0")
    resolved_currency_id = purchase_currency_id

    if rows is None:
        rows = []

    if not isinstance(rows, list):
        raise ValueError("purchase_payments_invalid")

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("purchase_payments_invalid")

        row_currency_id = row.get("currency_id")
        if not _asset_payment_currency_required(resolved_currency_id) and _asset_payment_currency_required(row_currency_id):
            resolved_currency_id = row_currency_id

        payment_method = _normalize_asset_payment_method(row.get("payment_method"))
        bank_id = row.get("bank_id")
        if _asset_payment_requires_bank(payment_method) and not bank_id:
            raise ValueError("bank_account_required")
        if payment_method == ASSET_PAYMENT_METHOD_CASH:
            bank_id = None

        amount = _to_decimal(row.get("amount"), default="0")
        if amount <= 0:
            raise ValueError("amount_required")

        normalized_rows.append(
            {
                "currency_id": None,
                "payment_method": payment_method,
                "bank_id": int(bank_id) if bank_id else None,
                "amount": amount,
            }
        )
        running_total += amount

    if not _asset_payment_currency_required(resolved_currency_id):
        if allow_empty and not normalized_rows:
            return []
        resolved_currency_id = _default_egp_currency_id()
        if not resolved_currency_id:
            raise ValueError("currency_required")

    resolved_currency_id = int(resolved_currency_id)
    for row in normalized_rows:
        row["currency_id"] = resolved_currency_id

    if not normalized_rows:
        if allow_empty:
            return []

        return [
            {
                "currency_id": resolved_currency_id,
                "payment_method": ASSET_PAYMENT_METHOD_CASH,
                "bank_id": None,
                "amount": _to_decimal(purchase_price),
            }
        ]

    target_total = _to_decimal(purchase_price)
    if running_total.quantize(Decimal("0.01")) != target_total.quantize(Decimal("0.01")):
        raise ValueError("purchase_payment_total_mismatch")

    return normalized_rows


def _get_asset_cash_balance_entry(currency_id, bank_id):
    qs = BalanceEntry.objects.select_for_update().filter(
        balance_type=BalanceEntry.BalanceType.CASH,
        currency_id=currency_id,
    )
    if bank_id:
        qs = qs.filter(bank_id=bank_id)
    else:
        qs = qs.filter(bank__isnull=True)
    return qs.order_by("id").first()


def _apply_asset_balance_delta(currency_id, payment_method, bank_id, amount_delta):
    delta = _to_decimal(amount_delta)
    if delta == 0:
        return

    resolved_method = _normalize_asset_payment_method(payment_method)
    resolved_bank_id = bank_id if _asset_payment_requires_bank(resolved_method) else None

    entry = _get_asset_cash_balance_entry(currency_id, resolved_bank_id)
    if not entry:
        raise ValueError("matching_balance_entry_not_found")

    next_amount = _to_decimal(entry.amount) + delta
    if next_amount < 0:
        raise ValueError("insufficient_balance")

    entry.amount = next_amount
    entry.save(update_fields=["amount"])


def _apply_asset_purchase_rows_delta(rows, sign):
    sign_multiplier = Decimal("1") if sign >= 0 else Decimal("-1")
    for row in rows:
        _apply_asset_balance_delta(
            currency_id=row.get("currency_id"),
            payment_method=row.get("payment_method"),
            bank_id=row.get("bank_id"),
            amount_delta=sign_multiplier * _to_decimal(row.get("amount")),
        )


def _purchase_rows_from_instances(instances):
    return [
        {
            "currency_id": item.currency_id,
            "payment_method": item.payment_method,
            "bank_id": item.bank_id,
            "amount": _to_decimal(item.amount),
        }
        for item in instances
    ]


def _sync_asset_purchase_payments(asset, rows):
    AssetPurchasePayment.objects.filter(asset=asset).delete()
    for row in rows:
        AssetPurchasePayment.objects.create(
            asset=asset,
            currency_id=row["currency_id"],
            payment_method=row["payment_method"],
            bank_id=row.get("bank_id"),
            amount=row["amount"],
        )


