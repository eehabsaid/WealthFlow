from django.db import models
from ..bank import Bank
from ..currency import Currency

class BalanceEntry(models.Model):
    title = models.CharField(max_length=200)
    
    # Clean, scalable choice definition
    class BalanceType(models.TextChoices):
        CASH = "cash", "Cash"
        BANK = "bank", "Bank Account"
        GOLD = "gold", "Gold"  # Matches frontend value="gold"
        CERTIFICATE = "certificate", "Certificate"

    balance_type = models.CharField(
        max_length=20,
        choices=BalanceType.choices,
        default=BalanceType.CASH
    )
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True)
    currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, null=True, blank=True
    )
    purity = models.CharField(max_length=20, blank=True, default="")
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    entry_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["title"]

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "balance_type":self.balance_type,
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "currency_id": self.currency_id,
            "currency_code": self.currency.code if self.currency else "",
            "currency_symbol": self.currency.symbol if self.currency else "",
            "currency_flag": self.currency.flag if self.currency else "💱",
            "currency_name": self.currency.name if self.currency else "",
            "purity": self.purity,
            "amount": float(self.amount),
            "notes": self.notes,
        }

    def __str__(self):
        return f"{self.title} ({self.currency.code if self.currency else 'Unknown'})"
