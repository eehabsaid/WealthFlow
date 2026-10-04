"""Orchestrates plan checkout: creates a pending Invoice, then either
hands off to Paymob (when configured) or reports fake/test mode so
trial users aren't blocked while Ehab sets up real payment keys.
"""

import logging
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

from core.models import Currency, Invoice, Plan
from core.services.billing.paymob_gateway import PaymobConfigError, PaymobGateway
from core.services.billing.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

_MERCHANT_ORDER_PREFIX = "wf-inv-"
# ISO country for Paymob's billing_data, per charge currency (placeholder "NA" otherwise).
_COUNTRY_BY_CURRENCY = {"EGP": "EG", "SAR": "SA", "AED": "AE"}


def amount_to_cents(amount) -> int:
    """Smallest-unit amount Paymob expects, rounded (never truncated)."""
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class CheckoutError(Exception):
    pass


def _billing_data_for(user, currency_code: str = "") -> dict:
    """Paymob requires a billing_data block; most fields aren't collected
    by WealthFlow, so placeholders are used where nothing real exists."""
    name = (getattr(user, "get_full_name", lambda: "")() or user.username or "Customer").strip()
    first, _, last = name.partition(" ")
    return {
        "first_name": first or "Customer",
        "last_name": last or "Customer",
        "email": getattr(user, "email", "") or "customer@example.com",
        "phone_number": "+00000000000",
        "apartment": "NA",
        "floor": "NA",
        "street": "NA",
        "building": "NA",
        "city": "NA",
        "country": _COUNTRY_BY_CURRENCY.get(str(currency_code).upper(), "NA"),
        "state": "NA",
    }


class CheckoutService:
    @staticmethod
    def _create_pending_invoice(user, plan: Plan, currency: Currency) -> Invoice:
        amount = plan.price_for(currency.code)
        if amount is None:
            raise CheckoutError("This plan has no price set in the selected currency.")

        subscription = SubscriptionService.get_subscription(user)
        if subscription is None:
            raise CheckoutError("No subscription found for this user.")

        now = timezone.now()
        return Invoice.objects.create(
            owner=user,
            subscription=subscription,
            plan=plan,
            amount=amount,
            currency=currency,
            status="pending",
            period_start=now,
            period_end=now + timedelta(days=plan.billing_interval_days),
        )

    @classmethod
    def initiate_checkout(cls, user, plan: Plan, currency: Currency) -> dict:
        # Once any real Paymob account exists, a currency it cannot charge is
        # refused up front — never silently sent to a different region's
        # account, and never downgraded to a fake payment.
        if PaymobGateway.any_configured() and not PaymobGateway.is_configured(currency.code):
            raise CheckoutError(
                f"Online payment is not available in {currency.code} yet. "
                "Please choose another currency or contact support."
            )

        invoice = cls._create_pending_invoice(user, plan, currency)

        if not PaymobGateway.any_configured():
            return {
                "mode": "fake",
                "invoice_id": invoice.id,
                "amount": str(invoice.amount),
                "currency_code": currency.code,
            }

        merchant_order_id = f"{_MERCHANT_ORDER_PREFIX}{invoice.id}"
        try:
            result = PaymobGateway.create_checkout(
                amount_cents=amount_to_cents(invoice.amount),
                currency_code=currency.code,
                merchant_order_id=merchant_order_id,
                billing_data=_billing_data_for(user, currency.code),
            )
        except PaymobConfigError as exc:
            invoice.status = "failed"
            invoice.save(update_fields=["status"])
            raise CheckoutError(str(exc)) from exc

        invoice.gateway_reference = str(result["order_id"])
        invoice.save(update_fields=["gateway_reference"])
        return {"mode": "paymob", "invoice_id": invoice.id, "iframe_url": result["iframe_url"]}

    @classmethod
    def complete_fake_payment(cls, user, invoice_id) -> Invoice:
        """Test-mode only. Stops working the moment Paymob is fully
        configured, so it can never be used to bypass real payment."""
        if PaymobGateway.any_configured():
            raise CheckoutError("Fake payments are disabled once a real payment gateway is configured.")

        invoice = (
            Invoice.objects.filter(id=invoice_id, owner=user, status="pending")
            .select_related("subscription", "plan")
            .first()
        )
        if invoice is None:
            raise CheckoutError("Invoice not found or already processed.")

        cls._mark_paid_and_activate(invoice)
        return invoice

    @classmethod
    def process_webhook(cls, payload: dict) -> Invoice | None:
        """Idempotent: repeated webhook deliveries for an already-paid
        invoice are a no-op."""
        obj = payload.get("obj", payload)
        order = obj.get("order") or {}
        merchant_order_id = str(order.get("merchant_order_id") or "")
        if not merchant_order_id.startswith(_MERCHANT_ORDER_PREFIX):
            return None

        invoice_id = merchant_order_id[len(_MERCHANT_ORDER_PREFIX):]
        invoice = (
            Invoice.objects.filter(id=invoice_id)
            .select_related("subscription", "plan", "currency")
            .first()
        )
        if invoice is None or invoice.status == "paid":
            return invoice

        if obj.get("pending") is True:
            return invoice  # Paymob will send the final result later; stay pending
        if obj.get("is_voided") is True or obj.get("is_refunded") is True:
            logger.warning("Paymob void/refund callback for invoice %s ignored (no activation).", invoice.id)
            return invoice

        if obj.get("success"):
            if not cls._matches_invoice(invoice, obj):
                logger.error("Paymob success callback for invoice %s does not match amount/currency; not activated.", invoice.id)
                return invoice
            cls._mark_paid_and_activate(invoice)
        else:
            invoice.status = "failed"
            invoice.save(update_fields=["status"])
        return invoice

    @staticmethod
    def _matches_invoice(invoice: Invoice, obj: dict) -> bool:
        """A signed success callback must be for exactly the amount and
        currency this invoice was issued in."""
        try:
            paid_cents = int(obj.get("amount_cents"))
        except (TypeError, ValueError):
            return False
        currency = str(obj.get("currency") or "").upper()
        return paid_cents == amount_to_cents(invoice.amount) and currency == str(invoice.currency.code).upper()

    @staticmethod
    def _mark_paid_and_activate(invoice: Invoice) -> None:
        now = timezone.now()
        invoice.status = "paid"
        invoice.paid_at = now
        invoice.save(update_fields=["status", "paid_at"])

        subscription = invoice.subscription
        subscription.plan = invoice.plan
        subscription.status = "active"
        subscription.current_period_end = invoice.period_end
        subscription.save(update_fields=["plan", "status", "current_period_end", "updated_at"])
