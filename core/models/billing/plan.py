from django.db import models


class Plan(models.Model):
    """A purchasable subscription tier (e.g. Basic, Pro, or any tier an
    admin creates). Prices live on PlanPrice, one row per app-configured
    Currency — see core.models.Currency (Settings > Currency)."""

    code = models.SlugField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    billing_interval_days = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def price_for(self, currency_code: str):
        price = self.prices.filter(currency__code=currency_code).select_related("currency").first()
        return price.amount if price else None

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "billing_interval_days": self.billing_interval_days,
            "is_active": self.is_active,
            "prices": [p.to_dict() for p in self.prices.select_related("currency").all()],
        }

    def __str__(self):
        return self.name
