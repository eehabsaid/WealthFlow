"""Sysadmin customer operations: suspend/unsuspend, extend trial, change plan, invoice paid/void, refund.

The Paymob client has no refund call, so a refund is RECORDED here (invoice -> refunded, access revoked when
that invoice was what granted it) and the money itself is returned from the Paymob dashboard; the result says so.
"""

from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from core.models import Invoice, Plan, Subscription
from core.services.billing.subscription_service import SubscriptionService

MAX_EXTEND_DAYS = 365
User = get_user_model()


class CustomerAdminError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def customer_dict(user, *, invoice_limit: int = 25) -> dict:
    sub = SubscriptionService.get_subscription(user)
    invoices = list(Invoice.objects.filter(owner=user).select_related("plan", "currency")[:invoice_limit])
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "subscription": sub.to_dict() if sub else None,
        "invoices": [i.to_dict() for i in invoices],
        "invoice_count": Invoice.objects.filter(owner=user).count(),
    }


def list_customers(search: str = "") -> list:
    qs = User.objects.filter(is_superuser=False).order_by("username")
    if search:
        qs = qs.filter(username__icontains=search) | qs.filter(email__icontains=search)
    return [customer_dict(u) for u in qs.distinct().order_by("username")]


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
def refund_invoice(invoice_id, *, amount=None, note: str = "", revoke_access: bool = True) -> dict:
    inv = _invoice(invoice_id)
    if inv.status != "paid":
        raise CustomerAdminError("bad_status", "Only a paid invoice can be refunded.")
    try:
        value = inv.amount if amount in (None, "") else Decimal(str(amount))
    except InvalidOperation:
        raise CustomerAdminError("bad_amount", "Invalid refund amount.")
    if value <= 0 or value > inv.amount:
        raise CustomerAdminError("bad_amount", "Refund must be greater than 0 and not exceed the invoice amount.")
    now = timezone.now()
    inv.status, inv.refunded_at, inv.refund_amount, inv.refund_note = "refunded", now, value, (note or "")[:255]
    inv.save(update_fields=["status", "refunded_at", "refund_amount", "refund_note"])

    revoked = False
    sub = inv.subscription
    if revoke_access and sub.status == "active" and sub.current_period_end == inv.period_end:
        sub.status, sub.canceled_at, sub.current_period_end = "canceled", now, now
        sub.save(update_fields=["status", "canceled_at", "current_period_end", "updated_at"])
        revoked = True
    via_paymob = bool(inv.gateway_reference)
    return {
        "invoice": inv.to_dict(),
        "access_revoked": revoked,
        "gateway_refund": "manual" if via_paymob else "not_applicable",
        "message": "Refund recorded. Return the money from the Paymob dashboard: the Paymob client has no refund API."
        if via_paymob
        else "Refund recorded.",
    }
