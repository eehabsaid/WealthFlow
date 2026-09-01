"""Keeps a read-only Expense mirror row in sync with a CreditCardPayment
record, so the outflow shows up in Expenses/dashboards like a manual
entry. Balance stays single-sourced from CreditCardPayment.apply_and_mirror
/ reverse_and_unmirror (see core/models/balance/credit_card_payment.py).

Sync mechanics live in core.services.shared.expense_mirror_engine and
are shared with core.services.fixed_assets' asset_expense_mirror_service
— this file only owns Credit-Card-specific naming/field mapping.
"""

from core.services.shared.expense_mirror_engine import (
    delete_mirror,
    get_or_create_mirror_subcategory,
    sync_mirror,
)

CREDIT_CARD_CATEGORY_NAME = "Credit Card"
CREDIT_CARD_CATEGORY_ICON = "💳"
CREDIT_CARD_CATEGORY_COLOR = "#dc3545"
CREDIT_CARD_SUBCATEGORY_NAME = "Credit Card Payment"

SOURCE_CREDIT_CARD_PAYMENT = "credit_card_payment"


def _get_or_create_credit_card_subcategory():
    return get_or_create_mirror_subcategory(
        CREDIT_CARD_CATEGORY_NAME,
        CREDIT_CARD_CATEGORY_ICON,
        CREDIT_CARD_CATEGORY_COLOR,
        CREDIT_CARD_SUBCATEGORY_NAME,
    )


def sync_credit_card_payment_mirror(payment):
    if payment is None or not payment.id:
        return None
    notes = "Auto-generated from a credit card payment. Read-only — edit/delete it from the Balance › Credit Card Payments tab instead."
    if payment.notes:
        notes = f"{notes}\n{payment.notes}"
    category, subcategory = _get_or_create_credit_card_subcategory()
    return sync_mirror(
        SOURCE_CREDIT_CARD_PAYMENT,
        payment.id,
        date_value=payment.payment_date,
        description=payment._description(),
        amount_egp=payment.amount_egp,
        payment_method=payment.payment_method,
        bank_id=payment.bank_id,
        notes=notes,
        category=category,
        subcategory=subcategory,
    )


def delete_credit_card_payment_mirror(payment_id):
    delete_mirror(SOURCE_CREDIT_CARD_PAYMENT, payment_id)
