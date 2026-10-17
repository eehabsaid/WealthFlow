"""Applies a verified Stripe event to the matching Invoice (idempotent)."""

from __future__ import annotations

import logging

from core.models import Invoice
from core.services.billing.stripe_gateway import MERCHANT_PREFIX, minor_units

logger = logging.getLogger(__name__)

_PAID_EVENTS = {"checkout.session.completed", "checkout.session.async_payment_succeeded"}
_FAILED_EVENTS = {"checkout.session.async_payment_failed", "checkout.session.expired"}


def process_stripe_event(event: dict) -> Invoice | None:
    from core.services.billing.checkout_service import CheckoutService

    kind = event.get("type")
    session = (event.get("data") or {}).get("object") or {}
    ref = str(session.get("client_reference_id") or "")
    if kind not in _PAID_EVENTS | _FAILED_EVENTS or not ref.startswith(MERCHANT_PREFIX):
        return None
    invoice = (
        Invoice.objects.filter(id=ref[len(MERCHANT_PREFIX):])
        .select_related("subscription", "plan", "currency")
        .first()
    )
    if invoice is None or invoice.status in ("paid", "refunded", "void"):
        return invoice  # a late/duplicate event never re-activates a paid, refunded or void invoice
    if kind in _FAILED_EVENTS:
        invoice.status = "failed"
        invoice.save(update_fields=["status"])
        return invoice
    if session.get("payment_status") != "paid":
        return invoice  # async method still pending; the async_payment_* event settles it
    code = invoice.currency.code
    if session.get("amount_total") != minor_units(invoice.amount, code) or str(session.get("currency") or "").upper() != code.upper():
        logger.error("Stripe event for invoice %s does not match amount/currency; not activated.", invoice.id)
        return invoice
    invoice.gateway = "stripe"
    invoice.gateway_transaction_id = str(session.get("payment_intent") or "")
    invoice.save(update_fields=["gateway", "gateway_transaction_id"])
    CheckoutService._mark_paid_and_activate(invoice)
    return invoice
