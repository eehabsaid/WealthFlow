from django.db import models


class PlanPrice(models.Model):
    """A Plan's price in one app-configured Currency (Settings > Currency).
    Admins add/edit these from the Billing Plans settings tab; the currency
    choices always come from core.models.Currency, never a hardcoded list."""

    plan = models.ForeignKey(
        "core.Plan",
        on_delete=models.CASCADE,
        related_name="prices",
    )
    currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="plan_prices",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("plan", "currency")
        ordering = ["currency__order", "currency__code"]

    def to_dict(self):
        return {
            "id": self.id,
            "currency_code": self.currency.code,
            "currency_symbol": self.currency.symbol,
            "amount": str(self.amount),
        }

    def __str__(self):
        return f"{self.plan.code}:{self.currency.code}={self.amount}"
