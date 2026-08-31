from django.db import models
from django.db import transaction
from decimal import Decimal
from ..bank import Bank
from ..currency import Currency
from .balance_entry import BalanceEntry


class BankInterest(models.Model):
    """Non-certificate bank interest credited to a bank account.

    Mirrors BalanceTransfer's apply/reverse pattern, but is single-sided:
    it only credits the destination bank's BalanceEntry (no source leg).
    """

    interest_date = models.DateField()
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-interest_date", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "interest_date": str(self.interest_date) if self.interest_date else "",
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "currency_id": self.currency_id,
            "currency_code": self.currency.code if self.currency else "",
            "currency_symbol": self.currency.symbol if self.currency else "",
            "currency_flag": self.currency.flag if self.currency else "💱",
            "currency_name": self.currency.name if self.currency else "",
            "amount": float(self.amount),
            "notes": self.notes or "",
        }

    def _get_or_create_balance_entry(self):
        entry = BalanceEntry.objects.filter(
            bank_id=self.bank_id,
            currency_id=self.currency_id,
        ).first()

        if not entry:
            title = "Cash"
            if self.bank_id:
                title = f"{self.bank.name} Account"

            entry = BalanceEntry.objects.create(
                title=f"{title} ({self.currency.code})",
                balance_type=BalanceEntry.BalanceType.BANK,
                bank_id=self.bank_id,
                currency_id=self.currency_id,
                amount=0,
                notes="Created automatically for bank interest",
            )

        return entry

    @transaction.atomic
    def apply_interest(self):
        entry = self._get_or_create_balance_entry()
        entry.amount = entry.amount + Decimal(str(self.amount))
        entry.save()

    @transaction.atomic
    def reverse_interest(self):
        entry = self._get_or_create_balance_entry()
        entry.amount = entry.amount - Decimal(str(self.amount))
        entry.save()

    def __str__(self):
        return f"{self.bank.name if self.bank else 'Unknown'} interest ({self.amount})"
