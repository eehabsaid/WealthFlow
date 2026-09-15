from django.conf import settings
from django.db import models

from core.constants import UPGRADE_REQUEST_STATUS_CHOICES


class UpgradeRequest(models.Model):
    """A customer's request to move to a different Plan, captured while
    gateway checkout (Paymob/Stripe) isn't wired up yet. One pending
    request per user — submitting again just updates the plan on it."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="upgrade_requests",
    )
    plan = models.ForeignKey(
        "core.Plan",
        on_delete=models.CASCADE,
        related_name="upgrade_requests",
    )
    currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="upgrade_requests",
    )
    status = models.CharField(max_length=20, choices=UPGRADE_REQUEST_STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "plan_name": self.plan.name,
            "currency_code": self.currency.code if self.currency else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"UpgradeRequest({self.owner.username} -> {self.plan.code}, {self.status})"
