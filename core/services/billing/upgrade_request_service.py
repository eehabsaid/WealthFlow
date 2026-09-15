"""Handles the "I want to upgrade" flow while gateway checkout (Paymob/
Stripe) isn't wired up yet. Requests are admin-visible so Ehab can follow
up manually until real checkout lands.
"""

from core.models import Currency, Plan, UpgradeRequest


class UpgradeRequestService:
    @staticmethod
    def get_pending(user) -> UpgradeRequest | None:
        return (
            UpgradeRequest.objects.filter(owner=user, status="pending")
            .select_related("plan", "currency")
            .first()
        )

    @classmethod
    def submit(cls, user, plan: Plan, currency: Currency | None = None) -> UpgradeRequest:
        """Idempotent: a user has at most one pending request. Submitting
        again (e.g. picking a different plan) just updates the existing
        pending row instead of creating duplicates."""
        existing = cls.get_pending(user)
        if existing is not None:
            existing.plan = plan
            existing.currency = currency
            existing.save(update_fields=["plan", "currency", "updated_at"])
            return existing

        return UpgradeRequest.objects.create(owner=user, plan=plan, currency=currency)
