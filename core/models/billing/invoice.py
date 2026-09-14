from django.conf import settings
from django.db import models

from core.constants import INVOICE_STATUS_CHOICES


class Invoice(models.Model):
    """A single billing charge attempt/record for a subscription period."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    subscription = models.ForeignKey(
        "core.Subscription",
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default="pending")
    gateway_reference = models.CharField(max_length=255, blank=True, default="")
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_at", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "amount": str(self.amount),
            "currency": self.currency.code,
            "status": self.status,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }

    def __str__(self):
        return f"Invoice({self.owner.username}, {self.amount} {self.currency.code}, {self.status})"
