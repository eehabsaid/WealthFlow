from django.db import models
from django.db import transaction
from decimal import Decimal
from ..bank import Bank
from ..currency import Currency
from .balance_entry import BalanceEntry

class BalanceTransfer(models.Model):
    class TransferType(models.TextChoices):
        BANK_TO_BANK = "bank_to_bank", "Bank to Bank"
        BANK_TO_CASH = "bank_to_cash", "Bank to Cash"
        CASH_TO_BANK = "cash_to_bank", "Cash to Bank"

    transfer_date = models.DateField()
    transfer_type = models.CharField(
        max_length=20,
        choices=TransferType.choices
    )
    from_bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True, related_name="transfers_out")
    to_bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True, related_name="transfers_in")
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    fee = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-transfer_date", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "transfer_date": str(self.transfer_date) if self.transfer_date else "",
            "transfer_type": self.transfer_type,
            "from_bank_id": self.from_bank_id,
            "from_bank_name": self.from_bank.name if self.from_bank else "",
            "to_bank_id": self.to_bank_id,
            "to_bank_name": self.to_bank.name if self.to_bank else "",
            "currency_id": self.currency_id,
            "currency_code": self.currency.code if self.currency else "",
            "currency_symbol": self.currency.symbol if self.currency else "",
            "currency_flag": self.currency.flag if self.currency else "💱",
            "currency_name": self.currency.name if self.currency else "",
            "amount": float(self.amount),
            "fee": float(self.fee),
            "notes": self.notes or "",
        }

    def _get_or_create_balance_entry(self, is_source):
        # Determine bank based on transfer type and source/dest
        bank_id = None
        is_cash = False
        
        if self.transfer_type == self.TransferType.BANK_TO_BANK:
            bank_id = self.from_bank_id if is_source else self.to_bank_id
        elif self.transfer_type == self.TransferType.BANK_TO_CASH:
            if is_source:
                bank_id = self.from_bank_id
            else:
                is_cash = True
        elif self.transfer_type == self.TransferType.CASH_TO_BANK:
            if is_source:
                is_cash = True
            else:
                bank_id = self.to_bank_id

        # To avoid creating duplicates when user has Bank Accounts with type=Cash,
        # we only filter by bank_id and currency.
        if is_cash:
            entry = BalanceEntry.objects.filter(
                balance_type=BalanceEntry.BalanceType.CASH,
                bank_id__isnull=True,
                currency_id=self.currency_id
            ).first()
        else:
            entry = BalanceEntry.objects.filter(
                bank_id=bank_id,
                currency_id=self.currency_id
            ).first()

        if not entry:
            title = "Cash"
            if bank_id:
                bank_obj = Bank.objects.get(id=bank_id)
                title = f"{bank_obj.name} Account"
                
            entry = BalanceEntry.objects.create(
                title=f"{title} ({self.currency.code})",
                balance_type=BalanceEntry.BalanceType.CASH if is_cash else BalanceEntry.BalanceType.BANK,
                bank_id=bank_id,
                currency_id=self.currency_id,
                amount=0,
                notes="Created automatically for balance transfer"
            )
            
        return entry

    @transaction.atomic
    def apply_transfer(self):
        source_entry = self._get_or_create_balance_entry(is_source=True)
        dest_entry = self._get_or_create_balance_entry(is_source=False)
        
        amt = Decimal(str(self.amount))
        f = Decimal(str(self.fee))
        
        if source_entry.amount < (amt + f):
            raise ValueError("insufficient_balance")
        
        source_entry.amount = source_entry.amount - amt - f
        source_entry.save()
        
        dest_entry.amount = dest_entry.amount + amt
        dest_entry.save()

    @transaction.atomic
    def reverse_transfer(self):
        source_entry = self._get_or_create_balance_entry(is_source=True)
        dest_entry = self._get_or_create_balance_entry(is_source=False)
        
        amt = Decimal(str(self.amount))
        f = Decimal(str(self.fee))
        
        source_entry.amount = source_entry.amount + amt + f
        source_entry.save()
        
        dest_entry.amount = dest_entry.amount - amt
        dest_entry.save()
