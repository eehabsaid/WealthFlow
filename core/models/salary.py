from django.db import models
from .company import Company
from .currency import Currency
from .bank import Bank

class SalaryEntry(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="salary_entries"
    )
    year = models.IntegerField()
    month = models.CharField(max_length=50)
    expected = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["year", "month"]
        unique_together = ["company", "year", "month"]

    @property
    def remaining(self):
        """Remaining = Expected - Paid, but never below 0 (per Excel logic)."""
        return max(0.0, float(self.expected) - float(self.paid))

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "company_name": self.company.name,
            "year": self.year,
            "month": self.month,
            "expected": float(self.expected),
            "paid": float(self.paid),
            "bonus": float(self.bonus),
            "remaining": self.remaining,
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.company.name} - {self.year} {self.month}"


class PerDiem(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="per_diems")
    year = models.IntegerField()
    date = models.DateField()
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="per_diems")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_egp = models.DecimalField(max_digits=12, decimal_places=2)
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True, related_name="per_diems")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "company_name": self.company.name,
            "year": self.year,
            "date": self.date.isoformat() if self.date else "",
            "currency_id": self.currency_id,
            "currency_code": self.currency.code,
            "currency_flag": self.currency.flag,
            "amount": float(self.amount),
            "amount_egp": float(self.amount_egp),
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
