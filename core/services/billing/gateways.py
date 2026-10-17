"""Gateway selection: which configured gateway charges / refunds a currency."""

from __future__ import annotations

from core.services.billing.gateway_base import GatewayError, PaymentGateway
from core.services.billing.paymob_gateway import PaymobGateway
from core.services.billing.paymob_refund import paymob_refund
from core.services.billing.stripe_gateway import StripeGateway


def select_gateway(currency_code: str) -> str | None:
    """'paymob' when a Paymob account can charge the currency, else 'stripe' when
    Stripe is set up for it, else None. Paymob wins so existing setups never change."""
    if PaymobGateway.is_configured(currency_code):
        return "paymob"
    if StripeGateway.is_configured(currency_code):
        return "stripe"
    return None


def any_gateway_configured() -> bool:
    """True once ANY real gateway exists -- this is what switches fake/test payments off."""
    return bool(PaymobGateway.any_configured() or StripeGateway.is_configured())


def gateway_is_configured(name: str, currency_code: str) -> bool:
    if name == "paymob":
        return PaymobGateway.is_configured(currency_code)
    if name == "stripe":
        return StripeGateway.is_configured()
    return False


def refund_through_gateway(invoice, amount) -> dict | None:
    """Refunds at the gateway that took the payment. Returns None when the invoice never
    went through a gateway (manual/test record). Raises GatewayError unless confirmed."""
    name = invoice.gateway or ("paymob" if invoice.gateway_reference else "")
    if name == "stripe":
        return {"gateway": "stripe", **StripeGateway.refund(invoice, amount)}
    if name == "paymob":
        return {"gateway": "paymob", **paymob_refund(invoice, amount)}
    return None


__all__ = ["GatewayError", "PaymentGateway", "any_gateway_configured", "gateway_is_configured", "refund_through_gateway", "select_gateway"]
