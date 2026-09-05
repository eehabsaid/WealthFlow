from django.db import models
from django.db.models import Case, Value, When
from datetime import date, datetime

from core.models.bank import Bank
from core.models.currency import Currency


class BankCertificate(models.Model):
    bank = models.ForeignKey(
        Bank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="certificates",
    )
    currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, null=True, blank=True
    )
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    interest_rate = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    interest_value = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    frequency = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=50, default="Active", blank=True)
    last_interest_posted_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            Case(
                When(status__iexact="closed", then=Value(1)),
                default=Value(0),
                output_field=models.IntegerField(),
            ),
            "issue_date__day",
            "bank__name",
        ]

    def to_dict(self):
        return {
            "id": self.id,
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "currency_id": self.currency_id,
            "currency_code": self.currency.code if self.currency else "",
            "currency_symbol": self.currency.symbol if self.currency else "",
            "currency_flag": self.currency.flag if self.currency else "💱",
            "issue_date": (
                self.issue_date.isoformat()
                if isinstance(self.issue_date, (date, datetime))
                else (self.issue_date or "")
            ),
            "expiry_date": (
                self.expiry_date.isoformat()
                if isinstance(self.expiry_date, (date, datetime))
                else (self.expiry_date or "")
            ),
            "amount": float(self.amount),
            "interest_rate": float(self.interest_rate),
            "interest_value": float(self.interest_value),
            "frequency": self.frequency,
            "status": self.status,
            "last_interest_posted_date": (
                self.last_interest_posted_date.isoformat()
                if isinstance(self.last_interest_posted_date, (date, datetime))
                else (self.last_interest_posted_date or "")
            ),
            "notes": self.notes,
        }

    def __str__(self):
        bank_name = self.bank.name if self.bank else "Unknown Bank"
        return f"{bank_name} Certificate {self.id}"
