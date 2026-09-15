"""Orchestrates plan checkout: creates a pending Invoice, then either
hands off to Paymob (when configured) or reports fake/test mode so
trial users aren't blocked while Ehab sets up real payment keys.
"""

from datetime import timedelta

from django.utils import timezone

from core.models import Currency, Invoice, Plan
from core.services.billing.paymob_gateway import PaymobConfigError, PaymobGateway
from core.services.billing.subscription_service import SubscriptionService

_MERCHANT_ORDER_PREFIX = "wf-inv-"


class CheckoutError(Exception):
    pass


def _billing_data_for(user) -> dict:
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
        "country": "NA",
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
        invoice = cls._create_pending_invoice(user, plan, currency)

        if not PaymobGateway.is_configured():
            return {
                "mode": "fake",
                "invoice_id": invoice.id,
                "amount": str(invoice.amount),
                "currency_code": currency.code,
            }

        merchant_order_id = f"{_MERCHANT_ORDER_PREFIX}{invoice.id}"
        try:
            result = PaymobGateway.create_checkout(
                amount_cents=int(invoice.amount * 100),
                currency_code=currency.code,
                merchant_order_id=merchant_order_id,
                billing_data=_billing_data_for(user),
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
        if PaymobGateway.is_configured():
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
            .select_related("subscription", "plan")
            .first()
        )
        if invoice is None or invoice.status == "paid":
            return invoice

        if obj.get("success"):
            cls._mark_paid_and_activate(invoice)
        else:
            invoice.status = "failed"
            invoice.save(update_fields=["status"])
        return invoice

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
