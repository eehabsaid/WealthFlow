# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

from core.constants import (
    ASSET_PAYMENT_METHOD_CASH,
)
from core.utils import _to_decimal

from core.services.fixed_assets.asset_purchase_service import _asset_payment_currency_required, _asset_payment_requires_bank, _default_egp_currency_id, _normalize_asset_payment_method


def _resolve_sale_deposit_values(data, existing_sale=None):
    fallback_currency_id = _default_egp_currency_id()

    existing_currency_id = existing_sale.deposit_currency_id if existing_sale else None
    currency_id = data.get("deposit_currency_id", existing_currency_id or fallback_currency_id)
    if not _asset_payment_currency_required(currency_id):
        raise ValueError("currency_required")

    existing_method = existing_sale.deposit_method if existing_sale else ASSET_PAYMENT_METHOD_CASH
    method = _normalize_asset_payment_method(data.get("deposit_method", existing_method))

    existing_bank_id = existing_sale.deposit_bank_id if existing_sale else None
    bank_id = data.get("deposit_bank_id", existing_bank_id)
    if _asset_payment_requires_bank(method) and not bank_id:
        raise ValueError("bank_account_required")
    if method == ASSET_PAYMENT_METHOD_CASH:
        bank_id = None

    return {
        "deposit_currency_id": int(currency_id),
        "deposit_method": method,
        "deposit_bank_id": int(bank_id) if bank_id else None,
    }


def _sale_payment_row(sale):
    currency_id = sale.deposit_currency_id or _default_egp_currency_id()
    method = _normalize_asset_payment_method(sale.deposit_method or ASSET_PAYMENT_METHOD_CASH)
    bank_id = sale.deposit_bank_id if _asset_payment_requires_bank(method) else None
    return {
        "currency_id": currency_id,
        "payment_method": method,
        "bank_id": bank_id,
        "amount": _to_decimal(sale.net_sale_amount),
    }


