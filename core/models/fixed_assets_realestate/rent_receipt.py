from decimal import Decimal

from django.conf import settings
from django.db import models, transaction

from core.models.balance.balance_entry import BalanceEntry
from core.models.currency import Currency
from core.models.fixed_assets_realestate.asset_rental import AssetRental


class RentReceipt(models.Model):
    """Rent actually received for one calendar month of a rental.

    Settles that month: while a receipt exists the virtual "<asset> Rental Income" line (monthly rent x occupancy)
    is left out of the projected balances, so the money counts once (as the real deposit made here).
    Uses the app-wide apply/reverse balance pattern; the logic lives in RentReceiptService.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="rent_receipts"
    )
    rental = models.ForeignKey(AssetRental, on_delete=models.CASCADE, related_name="receipts")
    period_start = models.DateField(help_text="First day of the month this payment settles.")
    received_date = models.DateField()
    bank = models.ForeignKey("Bank", on_delete=models.SET_NULL, null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_start", "-id"]
        constraints = [models.UniqueConstraint(fields=["rental", "period_start"], name="uniq_rent_receipt_month")]

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.rental.asset_id,
            "period": self.period_start.strftime("%Y-%m"),
            "received_date": str(self.received_date),
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "currency_code": self.currency.code,
            "amount": float(self.amount),
            "notes": self.notes,
        }

    def _balance_entry(self):
        is_bank = bool(self.bank_id)
        entry = BalanceEntry.objects.filter(owner=self.owner, bank_id=self.bank_id, currency_id=self.currency_id).first()
        if entry is None:
            entry = BalanceEntry.objects.create(
                owner=self.owner,
                title=f"{self.bank.name} Account ({self.currency.code})" if is_bank else f"Cash ({self.currency.code})",
                balance_type=BalanceEntry.BalanceType.BANK if is_bank else BalanceEntry.BalanceType.CASH,
                bank_id=self.bank_id,
                currency_id=self.currency_id,
                amount=0,
                notes="Created automatically for rent received",
            )
        return entry

    @transaction.atomic
    def apply_receipt(self):
        entry = self._balance_entry()
        entry.amount = entry.amount + Decimal(str(self.amount))
        entry.save()

    @transaction.atomic
    def reverse_receipt(self):
        entry = self._balance_entry()
        entry.amount = entry.amount - Decimal(str(self.amount))
        entry.save()
