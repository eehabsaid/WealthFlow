from django.conf import settings
from django.db import models
from django.utils import timezone

from core.constants import (
    GATEWAY_CHOICES,
    SUBSCRIPTION_ACCESS_STATUSES,
    SUBSCRIPTION_STATUS_CHOICES,
)


class Subscription(models.Model):
    """One subscription record per user. `owner` follows the app-wide
    multi-tenancy convention (has_user_field looks for `owner`, not `user`)."""

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        "core.Plan",
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default="trialing")
    trial_end = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES, default="none")
    gateway_customer_id = models.CharField(max_length=255, blank=True, default="")
    gateway_subscription_id = models.CharField(max_length=255, blank=True, default="")

    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def is_trialing(self):
        return self.status == "trialing"

    def trial_days_remaining(self):
        if not self.trial_end:
            return 0
        remaining = (self.trial_end - timezone.now()).days
        return max(remaining, 0)

    def has_access(self):
        """Whether the user should currently be let into the app."""
        if self.status == "trialing" and self.trial_end and timezone.now() >= self.trial_end:
            return False
        return self.status in SUBSCRIPTION_ACCESS_STATUSES

    def to_dict(self):
        return {
            "plan": self.plan.to_dict(),
            "status": self.status,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
            "trial_days_remaining": self.trial_days_remaining() if self.is_trialing() else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "gateway": self.gateway,
            "has_access": self.has_access(),
        }

    def __str__(self):
        return f"Subscription({self.owner.username}, {self.plan.code}, {self.status})"
