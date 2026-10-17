"""Sysadmin customer operations: suspend/unsuspend, extend trial, change plan, invoice paid/void, refund.

A refund of a gateway-paid invoice (Paymob or Stripe) is made at the gateway FIRST; the invoice becomes
"refunded" (and access is revoked when that invoice granted it) only after the gateway confirms. A failed call
changes nothing. The sysadmin can choose manual=True to just record a refund returned by hand (dashboard); the
same manual record is used automatically when the gateway is not configured or in test mode, and the result says so.
"""

from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from core.models import Invoice, Plan, Subscription
from core.services.billing.checkout_helpers import test_payments_allowed
from core.services.billing.gateway_base import GatewayError
from core.services.billing.gateways import gateway_is_configured, refund_through_gateway
from core.services.billing.subscription_service import SubscriptionService

MAX_EXTEND_DAYS = 365
User = get_user_model()


class CustomerAdminError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _sub(user) -> Subscription:
    sub = SubscriptionService.get_subscription(user)
    if sub is None:
        raise CustomerAdminError("no_subscription", "This user has no subscription.", 404)
    return sub


def _guard_target(user, actor=None):
    if user.is_superuser or (actor is not None and user.pk == actor.pk):
        raise CustomerAdminError("protected_user", "This account cannot be changed from here.", 403)


def suspend(user, actor=None) -> Subscription:
    _guard_target(user, actor)
    sub = _sub(user)
    sub.status = "suspended"
    sub.save(update_fields=["status", "updated_at"])
    return sub


def unsuspend(user, actor=None) -> Subscription:
    _guard_target(user, actor)
    sub = _sub(user)
    if sub.status != "suspended":
        raise CustomerAdminError("not_suspended", "This subscription is not suspended.")
    now = timezone.now()
    if sub.current_period_end and sub.current_period_end > now:
        sub.status = "active"
    elif sub.trial_end and sub.trial_end > now:
        sub.status = "trialing"
    else:
        sub.status = "expired"
    sub.save(update_fields=["status", "updated_at"])
    return sub


def extend_trial(user, days) -> Subscription:
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = 0
    if not 1 <= days <= MAX_EXTEND_DAYS:
        raise CustomerAdminError("bad_days", f"days must be between 1 and {MAX_EXTEND_DAYS}.")
    sub = _sub(user)
    if sub.status not in ("trialing", "expired"):
        raise CustomerAdminError("not_in_trial", "Only a trialing or expired-trial subscription can be extended.")
    now = timezone.now()
    base = sub.trial_end if sub.trial_end and sub.trial_end > now else now
    sub.trial_end = base + timedelta(days=days)
    sub.status = "trialing"
    sub.save(update_fields=["trial_end", "status", "updated_at"])
    return sub


def change_plan(user, plan_id) -> Subscription:
    sub = _sub(user)
    plan = Plan.objects.filter(pk=plan_id, is_active=True).first()
    if plan is None:
        raise CustomerAdminError("bad_plan", "Plan not found or inactive.", 404)
    sub.plan = plan
    sub.save(update_fields=["plan", "updated_at"])
    return sub


def _invoice(invoice_id) -> Invoice:
    inv = Invoice.objects.select_related("subscription", "plan", "currency").filter(pk=invoice_id).first()
    if inv is None:
        raise CustomerAdminError("no_invoice", "Invoice not found.", 404)
    return inv


def mark_invoice_paid(invoice_id) -> Invoice:
    from core.services.billing.checkout_service import CheckoutService

    inv = _invoice(invoice_id)
    if inv.status not in ("pending", "failed"):
        raise CustomerAdminError("bad_status", f"A {inv.status} invoice cannot be marked paid.")
    CheckoutService._mark_paid_and_activate(inv)
    return inv


def void_invoice(invoice_id) -> Invoice:
    inv = _invoice(invoice_id)
    if inv.status not in ("pending", "failed"):
        raise CustomerAdminError("bad_status", f"A {inv.status} invoice cannot be voided (refund it instead).")
    inv.status = "void"
    inv.save(update_fields=["status"])
    return inv


@transaction.atomic
def refund_invoice(invoice_id, *, amount=None, note: str = "", revoke_access: bool = True, manual: bool = False) -> dict:
    inv = _invoice(invoice_id)
    if inv.status != "paid":
        raise CustomerAdminError("bad_status", "Only a paid invoice can be refunded.")
    try:
        value = inv.amount if amount in (None, "") else Decimal(str(amount))
    except InvalidOperation:
        raise CustomerAdminError("bad_amount", "Invalid refund amount.")
    if value <= 0 or value > inv.amount:
        raise CustomerAdminError("bad_amount", "Refund must be greater than 0 and not exceed the invoice amount.")
    gateway_name = inv.gateway or ("paymob" if inv.gateway_reference else "")
    via_gateway = bool(gateway_name) and not manual and not test_payments_allowed() and gateway_is_configured(gateway_name, inv.currency.code)
    if via_gateway:
        try:
            refund_through_gateway(inv, value)
        except GatewayError as exc:
            raise CustomerAdminError("gateway_refund_failed", f"{exc} Nothing was changed. Fix it, or tick 'record only' if you returned the money yourself.", 502)
    now = timezone.now()
    inv.status, inv.refunded_at, inv.refund_amount, inv.refund_note = "refunded", now, value, (note or "")[:255]
    inv.save(update_fields=["status", "refunded_at", "refund_amount", "refund_note"])

    revoked = False
    sub = inv.subscription
    if revoke_access and sub.status == "active" and sub.current_period_end == inv.period_end:
        sub.status, sub.canceled_at, sub.current_period_end = "canceled", now, now
        sub.save(update_fields=["status", "canceled_at", "current_period_end", "updated_at"])
        revoked = True
    if via_gateway:
        outcome, message = "gateway", f"Refund confirmed by {gateway_name.title()} and recorded."
    elif gateway_name:
        outcome = "manual"
        message = f"Refund recorded only. Return the money from the {gateway_name.title()} dashboard."
    else:
        outcome, message = "not_applicable", "Refund recorded."
    return {"invoice": inv.to_dict(), "access_revoked": revoked, "gateway_refund": outcome, "message": message}
