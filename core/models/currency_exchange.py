from django.db import models, transaction
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal
from .currency import Currency
from .balance import BalanceEntry

class CurrencyExchange(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        REVERSED = "REVERSED", "Reversed"
        EDITED = "EDITED", "Edited"

    exchange_date = models.DateField()
    from_balance = models.ForeignKey(
        BalanceEntry, on_delete=models.PROTECT, related_name="exchanges_out"
    )
    to_balance = models.ForeignKey(
        BalanceEntry, on_delete=models.PROTECT, related_name="exchanges_in"
    )
    from_currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="exchanges_from"
    )
    to_currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="exchanges_to"
    )
    from_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    to_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=6, default=1)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    notes = models.TextField(blank=True, null=True)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="currency_exchanges"
    )
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reversed_currency_exchanges"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-exchange_date", "-id"]

    def to_dict(self):
        from_bank_name = self.from_balance.bank.name if self.from_balance and self.from_balance.bank else ""
        to_bank_name = self.to_balance.bank.name if self.to_balance and self.to_balance.bank else ""

        from_title = f"{self.from_balance.title}" if self.from_balance else ""
        to_title = f"{self.to_balance.title}" if self.to_balance else ""

        return {
            "id": self.id,
            "exchange_date": str(self.exchange_date) if self.exchange_date else "",
            "from_balance_id": self.from_balance_id,
            "from_balance_title": from_title,
            "from_bank_name": from_bank_name,
            "from_currency_id": self.from_currency_id,
            "from_currency_code": self.from_currency.code if self.from_currency else "",
            "from_currency_symbol": self.from_currency.symbol if self.from_currency else "",
            "from_currency_flag": self.from_currency.flag if self.from_currency else "💱",
            "from_amount": float(self.from_amount),
            "to_balance_id": self.to_balance_id,
            "to_balance_title": to_title,
            "to_bank_name": to_bank_name,
            "to_currency_id": self.to_currency_id,
            "to_currency_code": self.to_currency.code if self.to_currency else "",
            "to_currency_symbol": self.to_currency.symbol if self.to_currency else "",
            "to_currency_flag": self.to_currency.flag if self.to_currency else "💱",
            "to_amount": float(self.to_amount),
            "exchange_rate": float(self.exchange_rate),
            "status": self.status,
            "notes": self.notes or "",
            "user_username": self.user.username if self.user else "System",
            "reversed_at": self.reversed_at.strftime("%Y-%m-%d %H:%M") if self.reversed_at else "",
            "reversed_by_username": self.reversed_by.username if self.reversed_by else "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
        }

    @transaction.atomic
    def apply_exchange(self):
        if self.from_balance_id == self.to_balance_id:
            raise ValueError("same_balance_error")
        if self.from_amount <= 0 or self.to_amount <= 0 or self.exchange_rate <= 0:
            raise ValueError("invalid_amount_error")
        
        # Ensure currencies match balance entries
        if self.from_balance.currency_id != self.from_currency_id:
            self.from_currency_id = self.from_balance.currency_id
        if self.to_balance.currency_id != self.to_currency_id:
            self.to_currency_id = self.to_balance.currency_id

        # Lock source balance row
        from_b = BalanceEntry.objects.select_for_update().get(id=self.from_balance_id)
        to_b = BalanceEntry.objects.select_for_update().get(id=self.to_balance_id)

        amt_from = Decimal(str(self.from_amount))
        amt_to = Decimal(str(self.to_amount))

        if from_b.amount < amt_from:
            raise ValueError("insufficient_balance_error")

        from_b.amount -= amt_from
        from_b.save()

        to_b.amount += amt_to
        to_b.save()

        self.status = self.Status.ACTIVE
        self.save()

    @transaction.atomic
    def reverse_exchange(self, user=None, is_edit=False):
        if self.status == self.Status.REVERSED and not is_edit:
            raise ValueError("already_reversed_error")

        from_b = BalanceEntry.objects.select_for_update().get(id=self.from_balance_id)
        to_b = BalanceEntry.objects.select_for_update().get(id=self.to_balance_id)

        amt_from = Decimal(str(self.from_amount))
        amt_to = Decimal(str(self.to_amount))

        from_b.amount += amt_from
        from_b.save()

        to_b.amount -= amt_to
        to_b.save()

        if is_edit:
            self.status = self.Status.EDITED
        else:
            self.status = self.Status.REVERSED
            self.reversed_at = timezone.now()
            if user and hasattr(user, "is_authenticated") and user.is_authenticated:
                self.reversed_by = user

        self.save()
