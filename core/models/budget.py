from django.conf import settings
from django.db import models

BUDGET_PERIOD_CHOICES = [
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
    ("yearly", "Yearly"),
]

RECURRING_FREQUENCY_CHOICES = [
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
    ("yearly", "Yearly"),
]


class Budget(models.Model):
    """A spending limit for a period, optionally scoped to one expense
    category (null category = overall budget across all categories)."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name="budgets",
    )
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        "ExpenseCategory", on_delete=models.CASCADE,
        null=True, blank=True, related_name="budgets",
    )
    period = models.CharField(max_length=10, choices=BUDGET_PERIOD_CHOICES, default="monthly")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.ForeignKey(
        "Currency", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    amount_base = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    alert_threshold_percent = models.IntegerField(default=80)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "name"]

    def _default_currency_code(self) -> str:
        from core.services.shared.base_currency import get_user_base_code

        return get_user_base_code(self.owner)

    def to_dict(self, spent_base=None):
        data = {
            "id": self.id,
            "name": self.name,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "",
            "category_icon": self.category.icon if self.category else "",
            "period": self.period,
            "amount": float(self.amount),
            "amount_base": float(self.amount_base),
            "currency_code": self.currency.code if self.currency else self._default_currency_code(),
            "alert_threshold_percent": self.alert_threshold_percent,
            "is_active": self.is_active,
        }
        if spent_base is not None:
            spent = float(spent_base)
            limit = float(self.amount_base) or 0.0
            data["spent_base"] = spent
            data["remaining_base"] = limit - spent
            data["percent_used"] = round((spent / limit) * 100, 1) if limit > 0 else 0.0
        return data

    def __str__(self):
        return f"{self.name} ({self.period})"


class RecurringTransaction(models.Model):
    """A recurring expense (bill, subscription, rent, ...) that is
    auto-posted as a real Expense row once its next_run_date is due."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name="recurring_transactions",
    )
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        "ExpenseCategory", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    subcategory = models.ForeignKey(
        "ExpenseSubcategory", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.ForeignKey(
        "Currency", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    payment_method = models.CharField(max_length=50, default="Cash")
    bank = models.ForeignKey(
        "Bank", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    frequency = models.CharField(max_length=10, choices=RECURRING_FREQUENCY_CHOICES, default="monthly")
    interval = models.IntegerField(default=1, help_text="Repeat every N periods")
    start_date = models.DateField()
    next_run_date = models.DateField()
    last_run_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["next_run_date", "name"]

    def _default_currency_code(self) -> str:
        from core.services.shared.base_currency import get_user_base_code

        return get_user_base_code(self.owner)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "",
            "subcategory_id": self.subcategory_id,
            "amount": float(self.amount),
            "currency_code": self.currency.code if self.currency else self._default_currency_code(),
            "payment_method": self.payment_method,
            "bank_id": self.bank_id,
            "frequency": self.frequency,
            "interval": self.interval,
            "start_date": self.start_date.isoformat() if self.start_date else "",
            "next_run_date": self.next_run_date.isoformat() if self.next_run_date else "",
            "last_run_date": self.last_run_date.isoformat() if self.last_run_date else "",
            "end_date": self.end_date.isoformat() if self.end_date else "",
            "is_active": self.is_active,
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.name} ({self.frequency})"
