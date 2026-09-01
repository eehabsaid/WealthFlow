from django.db import models
from django.db import transaction
from ..bank import Bank


class CardRenewalFee(models.Model):
    """A bank card renewal/annual fee charged directly by the issuing
    bank against its own account — not "paid via" a method the user
    chooses, unlike CreditCardPayment.

    Two side effects happen together, both driven from here (matching
    the CreditCardPayment / Fixed Assets payment pattern):
      1. The card's bank BalanceEntry is debited via
         expense_service._apply_expense_balance_delta (payment_method
         is always the internal "Bank" value — the fee is never paid
         by cash or a separate card).
      2. A read-only Expense mirror row is kept in sync via
         card_renewal_fee_mirror_service, so the fee shows up in
         Expenses/dashboards like any manual entry.
    """

    # Internal-only; not exposed as a user choice, since a renewal fee
    # is always deducted directly by the issuing bank.
    _PAYMENT_METHOD = "Bank"

    fee_date = models.DateField()
    bank = models.ForeignKey(Bank, on_delete=models.PROTECT)
    card_label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Free-text identifier for the renewed card, e.g. 'Visa Debit ****1234'.",
    )
    amount_egp = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fee_date", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "fee_date": str(self.fee_date) if self.fee_date else "",
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "card_label": self.card_label,
            "amount_egp": float(self.amount_egp),
            "notes": self.notes or "",
        }

    def _description(self):
        head = "Card Renewal Fee"
        if self.card_label:
            head = f"{head}: {self.card_label}"
        return head

    @transaction.atomic
    def apply_and_mirror(self):
        from core.services.expenses.expense_service import _apply_expense_balance_delta
        from core.services.balance.card_renewal_fee_mirror_service import (
            sync_card_renewal_fee_mirror,
        )

        _apply_expense_balance_delta(
            self._PAYMENT_METHOD, self.bank_id, -abs(self.amount_egp or 0)
        )
        sync_card_renewal_fee_mirror(self)

    @transaction.atomic
    def reverse_and_unmirror(self):
        from core.services.expenses.expense_service import _apply_expense_balance_delta
        from core.services.balance.card_renewal_fee_mirror_service import (
            delete_card_renewal_fee_mirror,
        )

        _apply_expense_balance_delta(
            self._PAYMENT_METHOD, self.bank_id, abs(self.amount_egp or 0)
        )
        delete_card_renewal_fee_mirror(self.id)

    def __str__(self):
        return f"{self.bank.name if self.bank else 'Unknown'} card renewal fee ({self.amount_egp})"
