from django.db import models

from core.models.bank import Bank
from core.models.currency import Currency
from core.models.certificate.bank_certificate import BankCertificate


class BankCertificateInterestHistory(models.Model):
    certificate = models.ForeignKey(
        BankCertificate,
        on_delete=models.CASCADE,
        related_name="interest_history",
    )
    posting_date = models.DateField()
    posting_period = models.CharField(max_length=50)
    interest_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["posting_date", "id"]
        unique_together = ["certificate", "posting_date"]

    def to_dict(self):
        return {
            "id": self.id,
            "certificate_id": self.certificate_id,
            "posting_date": self.posting_date.isoformat() if self.posting_date else "",
            "posting_period": self.posting_period,
            "interest_amount": float(self.interest_amount or 0),
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "currency_id": self.currency_id,
            "currency_code": self.currency.code if self.currency else "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }
