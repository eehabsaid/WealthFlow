from django.db import models

from core.constants import PLAN_CODE_CHOICES


class Plan(models.Model):
    """A purchasable subscription tier (e.g. Basic, Pro)."""

    code = models.CharField(max_length=20, choices=PLAN_CODE_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    price_egp = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    billing_interval_days = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "price_egp": str(self.price_egp),
            "price_usd": str(self.price_usd),
            "billing_interval_days": self.billing_interval_days,
            "is_active": self.is_active,
        }

    def __str__(self):
        return self.name
