from django.db import models
from django.db import transaction
from ..bank import Bank


PAYMENT_METHOD_CHOICES = [
    ("Card", "Card"),
    ("Bank Transfer", "Bank Transfer"),
]


class CreditCardPayment(models.Model):
    """A payment made to settle an untracked credit card, paid from a
    tracked bank via debit card or bank transfer.

    The credit card itself is never modeled — only the outflow from the
    paying bank. Two side effects happen together, both driven from
    here (not from BalanceEntry directly), matching the Fixed Assets
    payment_method/bank pattern:
      1. The paying bank's BalanceEntry is debited via
         expense_service._apply_expense_balance_delta (shared with the
         Expense CRUD and Fixed Assets payment paths, so insufficient-
         balance and cash/bank/card targeting rules stay in one place).
      2. A read-only Expense mirror row is kept in sync via
         asset_expense_mirror_service, so the spend shows up in
         Expenses/dashboards like any manual entry.
    """

    payment_date = models.DateField()
    bank = models.ForeignKey(Bank, on_delete=models.PROTECT)
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, default="Card"
    )
    card_label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Free-text identifier for the untracked credit card, e.g. 'Visa ****1234'.",
    )
    amount_egp = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-payment_date", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "payment_date": str(self.payment_date) if self.payment_date else "",
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "payment_method": self.payment_method,
            "card_label": self.card_label,
            "amount_egp": float(self.amount_egp),
            "notes": self.notes or "",
        }

    def _description(self):
        head = "Credit Card Payment"
        if self.card_label:
            head = f"{head}: {self.card_label}"
        return head

    @transaction.atomic
    def apply_and_mirror(self):
        from core.services.expenses.expense_service import _apply_expense_balance_delta
        from core.services.balance.credit_card_payment_mirror_service import (
            sync_credit_card_payment_mirror,
        )

        _apply_expense_balance_delta(
            self.payment_method, self.bank_id, -abs(self.amount_egp or 0)
        )
        sync_credit_card_payment_mirror(self)

    @transaction.atomic
    def reverse_and_unmirror(self):
        from core.services.expenses.expense_service import _apply_expense_balance_delta
        from core.services.balance.credit_card_payment_mirror_service import (
            delete_credit_card_payment_mirror,
        )

        _apply_expense_balance_delta(
            self.payment_method, self.bank_id, abs(self.amount_egp or 0)
        )
        delete_credit_card_payment_mirror(self.id)

    def __str__(self):
        return f"{self.bank.name if self.bank else 'Unknown'} card payment ({self.amount_egp})"
