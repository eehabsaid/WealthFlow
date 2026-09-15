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
        """Trial users start on the lowest-tier active plan (by sort_order),
        so this keeps working regardless of which codes admins define."""
        return Plan.objects.filter(is_active=True).order_by("sort_order", "id").first()

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
        """A user's plan "allows" a required plan if its sort_order is at
        least as high as the required plan's — i.e. tiers are ordered by
        sort_order (higher sort_order = higher tier), not by hardcoded codes.
        This keeps working no matter how many tiers admins define."""
        if user is not None and user.is_superuser:
            return True
        subscription = cls.get_subscription(user)
        if subscription is None or not subscription.has_access():
            return False
        required_plan = Plan.objects.filter(code=required_plan_code).first()
        if required_plan is None:
            return False
        return subscription.plan.sort_order >= required_plan.sort_order

    @classmethod
    def plan_allows_feature(cls, user, feature_flag: str) -> bool:
        """A user's plan "allows" a feature if the boolean flag with that
        name is set on their current Plan (e.g. `allows_ai_workspace`).
        Admin-configured per plan from the Billing Plans settings tab —
        never a hardcoded plan code/tier check, so it stays correct no
        matter how many tiers admins define or rename."""
        if user is not None and user.is_superuser:
            return True
        subscription = cls.get_subscription(user)
        if subscription is None or not subscription.has_access():
            return False
        return bool(getattr(subscription.plan, feature_flag, False))
