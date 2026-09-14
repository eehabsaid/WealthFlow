"""Subscription lifecycle: trial start, access checks, plan gating.

Gateway checkout/webhook handling (Paymob/Stripe) is intentionally not part
of this module yet — this covers the trial + gating foundation only.
"""

from django.utils import timezone
from datetime import timedelta

from core.constants import TRIAL_DAYS_DEFAULT
from core.models import Plan, Subscription


class SubscriptionService:
    @staticmethod
    def get_default_trial_plan():
        """Trial users start on Basic; they can upgrade to Pro at checkout."""
        plan = Plan.objects.filter(code="basic", is_active=True).first()
        if plan is None:
            plan = Plan.objects.filter(is_active=True).order_by("sort_order", "id").first()
        return plan

    @classmethod
    def start_trial(cls, user, trial_days: int = TRIAL_DAYS_DEFAULT) -> Subscription:
        """Idempotent: safe to call even if a subscription already exists."""
        existing = Subscription.objects.filter(owner=user).first()
        if existing is not None:
            return existing

        plan = cls.get_default_trial_plan()
        if plan is None:
            raise RuntimeError("No active Plan exists to start a trial with. Seed Plan rows first.")

        now = timezone.now()
        return Subscription.objects.create(
            owner=user,
            plan=plan,
            status="trialing",
            trial_end=now + timedelta(days=trial_days),
        )

    @staticmethod
    def get_subscription(user) -> Subscription | None:
        return Subscription.objects.filter(owner=user).select_related("plan").first()

    @classmethod
    def has_active_access(cls, user) -> bool:
        if user is None or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        subscription = cls.get_subscription(user)
        if subscription is None:
            return False
        if subscription.is_trialing() and not subscription.has_access():
            cls._expire_trial(subscription)
            return False
        return subscription.has_access()

    @staticmethod
    def _expire_trial(subscription: Subscription) -> None:
        subscription.status = "expired"
        subscription.save(update_fields=["status", "updated_at"])

    @classmethod
    def plan_allows(cls, user, required_plan_code: str) -> bool:
        """Pro-gated features: Pro subscribers pass; Basic subscribers don't."""
        if user is not None and user.is_superuser:
            return True
        subscription = cls.get_subscription(user)
        if subscription is None or not subscription.has_access():
            return False
        if required_plan_code == "basic":
            return True
        return subscription.plan.code == required_plan_code
