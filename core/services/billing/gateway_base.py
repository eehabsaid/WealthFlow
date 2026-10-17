"""Common contract every payment gateway (Paymob, Stripe) fulfils.

A gateway answers four questions: is it configured (for a currency), how do I
start a checkout, how do I refund a paid invoice, and (via its own webhook view)
did the customer pay. Everything gateway-specific stays in its own module.
"""

from __future__ import annotations


class GatewayError(Exception):
    """A gateway call failed or was refused; the message is safe to show a sysadmin."""


class PaymentGateway:
    name = ""

    @classmethod
    def is_configured(cls, currency_code: str | None = None) -> bool:
        raise NotImplementedError

    @classmethod
    def any_configured(cls) -> bool:
        return cls.is_configured()

    @classmethod
    def create_checkout(cls, *, invoice, user, return_base: str = "") -> dict:
        """Returns {"reference": <gateway order/session id>, "redirect_url": <where to send the customer>}."""
        raise NotImplementedError

    @classmethod
    def refund(cls, invoice, amount) -> dict:
        """Refunds `amount` of a paid invoice. Returns {"reference": <refund id>}.
        Raises GatewayError unless the gateway CONFIRMED the refund."""
        raise NotImplementedError
