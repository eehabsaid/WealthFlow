"""Keeps a read-only Expense mirror row in sync with a CardRenewalFee
record, so the fee shows up in Expenses/dashboards like a manual entry.
Balance stays single-sourced from CardRenewalFee.apply_and_mirror /
reverse_and_unmirror (see core/models/balance/card_renewal_fee.py).

Sync mechanics live in core.services.shared.expense_mirror_engine and
are shared with credit_card_payment_mirror_service and the Fixed
Assets mirror service — this file only owns Card-Renewal-Fee-specific
naming/field mapping.
"""

from core.services.shared.expense_mirror_engine import (
    delete_mirror,
    get_or_create_mirror_subcategory,
    sync_mirror,
)

CARD_FEE_CATEGORY_NAME = "Card Fees"
CARD_FEE_CATEGORY_ICON = "🔄"
CARD_FEE_CATEGORY_COLOR = "#fd7e14"
CARD_FEE_SUBCATEGORY_NAME = "Card Renewal Fee"

SOURCE_CARD_RENEWAL_FEE = "card_renewal_fee"


def _get_or_create_card_fee_subcategory():
    return get_or_create_mirror_subcategory(
        CARD_FEE_CATEGORY_NAME,
        CARD_FEE_CATEGORY_ICON,
        CARD_FEE_CATEGORY_COLOR,
        CARD_FEE_SUBCATEGORY_NAME,
    )


def sync_card_renewal_fee_mirror(fee):
    if fee is None or not fee.id:
        return None
    notes = "Auto-generated from a card renewal fee. Read-only — edit/delete it from the Balance › Card Renewal Fees tab instead."
    if fee.notes:
        notes = f"{notes}\n{fee.notes}"
    category, subcategory = _get_or_create_card_fee_subcategory()
    return sync_mirror(
        SOURCE_CARD_RENEWAL_FEE,
        fee.id,
        date_value=fee.fee_date,
        description=fee._description(),
        amount_egp=fee.amount_egp,
        payment_method=fee._PAYMENT_METHOD,
        bank_id=fee.bank_id,
        notes=notes,
        category=category,
        subcategory=subcategory,
    )


def delete_card_renewal_fee_mirror(fee_id):
    delete_mirror(SOURCE_CARD_RENEWAL_FEE, fee_id)
