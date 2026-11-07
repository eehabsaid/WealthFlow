from django.conf import settings
from django.db import models


class MonthlyIncomeAdjustment(models.Model):
    """Manual extra income an owner enters for ONE calendar month.

    Added on top of the computed income (salary + certificate interest + rental)
    in the Expenses Report, so every month carries only its own value.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name="income_adjustments",
    )
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "year", "month"], name="uniq_income_adjustment_month"),
        ]

    def to_dict(self):
        return {"id": self.id, "year": self.year, "month": self.month, "amount": float(self.amount)}
