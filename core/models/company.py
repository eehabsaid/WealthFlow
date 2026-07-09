from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Company(models.Model):
    name = models.CharField(max_length=200, unique=True)
    display_name = models.CharField(max_length=200)
    group_name = models.CharField(max_length=200, blank=True)
    color_hex = models.CharField(max_length=7, default="#0d6efd")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # NEW PAYROLL FIELDS
    current_salary_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_salary_currency = models.ForeignKey(
        "Currency",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="company_salary_currency",
    )
    payment_day = models.IntegerField(
        default=25,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
    )
    default_bank = models.ForeignKey(
        "Bank",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_default",
    )
    per_diem_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, blank=True
    )
    per_diem_currency = models.ForeignKey(
        "Currency",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="company_perdiem_currency",
    )
    bonus_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, blank=True
    )
    payroll_notes = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "group_name": self.group_name,
            "color_hex": self.color_hex,
            "is_active": self.is_active,
            "order": self.order,
            # NEW PAYROLL FIELDS
            "current_salary_amount": float(self.current_salary_amount),
            "current_salary_currency_id": self.current_salary_currency_id,
            "current_salary_currency": (
                self.current_salary_currency.code
                if self.current_salary_currency
                else None
            ),
            "payment_day": self.payment_day,
            "default_bank_id": self.default_bank_id,
            "default_bank": (
                self.default_bank.name if self.default_bank else None
            ),
            "per_diem_amount": float(self.per_diem_amount),
            "per_diem_currency_id": self.per_diem_currency_id,
            "per_diem_currency": (
                self.per_diem_currency.code
                if self.per_diem_currency
                else None
            ),
            "bonus_amount": float(self.bonus_amount),
            "payroll_notes": self.payroll_notes,
        }

    def __str__(self):
        return self.name
