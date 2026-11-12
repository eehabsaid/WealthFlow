"""Cash BalanceEntry lookup, validation and delta helpers."""

from decimal import Decimal
import logging

from .errors import CertificateBalanceMappingError, CertificateInsufficientBalanceError

logger = logging.getLogger(__name__)


def is_principal_released(status):
    """A certificate whose status is "Closed" (case-insensitive) no longer
    holds its principal: it has been returned to the cash balance. Every
    other status (Active, Renewed, custom ones...) keeps the principal held."""
    return str(status or "").strip().lower() == "closed"


def held_amount(amount, status):
    """Principal currently deducted from cash for a certificate."""
    if is_principal_released(status):
        return Decimal("0")
    return Decimal(amount or 0)


def _cash_balance_queryset(bank_id, currency_id, owner):
    from core.models import BalanceEntry

    return BalanceEntry.objects.filter(
        owner=owner,
        balance_type__iexact="cash",
        bank_id=bank_id,
        currency_id=currency_id,
    )


def find_cash_balance_entry(bank_id, currency_id, owner, for_update=False):
    """Return the matching cash BalanceEntry for (bank_id, currency_id), or
    None. Logs a warning if more than one candidate row exists (ambiguous
    mapping); the lowest-id row is used deterministically."""
    qs = _cash_balance_queryset(bank_id, currency_id, owner).order_by("id")
    if for_update:
        qs = qs.select_for_update()

    rows = list(qs[:2])
    if not rows:
        return None
    if len(rows) > 1:
        logger.warning(
            "Multiple cash BalanceEntry rows match bank_id=%s currency_id=%s; "
            "using id=%s",
            bank_id, currency_id, rows[0].id,
        )
    return rows[0]


def validate_balance_entry_exists(bank_id, currency_id, owner):
    """Raise CertificateBalanceMappingError if there is no cash BalanceEntry
    for this bank/currency pair. Called from pre_save so it blocks the
    certificate write entirely."""
    if find_cash_balance_entry(bank_id, currency_id, owner) is None:
        raise CertificateBalanceMappingError(
            "There's no cash balance set up yet for this bank and currency. "
            "Please add one first, then save the certificate again."
        )


def validate_sufficient_balance(bank_id, currency_id, new_amount, old_snapshot, owner):
    """Raise CertificateInsufficientBalanceError if the matching cash entry
    cannot cover `new_amount` (the principal to be held after the save; 0 for
    a closed certificate). If `old_snapshot` (old_bank_id, old_currency_id,
    old_held_amount) applies to the SAME bank/currency as the new values, its
    amount is added back before checking - i.e. only the net delta must be
    covered. Assumes the matching entry already exists (call
    validate_balance_entry_exists first)."""
    entry = find_cash_balance_entry(bank_id, currency_id, owner)
    if entry is None:
        return  # existence already validated separately; nothing to check

    available = Decimal(entry.amount)
    if old_snapshot is not None:
        old_bank_id, old_currency_id, old_amount = old_snapshot
        if old_bank_id == bank_id and old_currency_id == currency_id:
            available += Decimal(old_amount)

    if available < Decimal(new_amount or 0):
        raise CertificateInsufficientBalanceError(
            "The matching cash balance doesn't have enough funds to cover "
            "this certificate's amount. Please lower the amount or top up "
            "the balance, then try again."
        )


def apply_delta(bank_id, currency_id, delta, owner):
    """Add `delta` (Decimal, can be negative) to the matched cash balance
    entry's amount. No-op (with a warning) if no matching entry is found.
    Note: bank_id may legitimately be None (matches cash entries with no
    bank assigned) - only currency_id is required."""
    if currency_id is None or delta == 0:
        return
    entry = find_cash_balance_entry(bank_id, currency_id, owner, for_update=True)
    if entry is None:
        logger.warning(
            "Cannot apply certificate balance delta: no cash BalanceEntry "
            "for bank_id=%s currency_id=%s", bank_id, currency_id,
        )
        return
    entry.amount = Decimal(entry.amount) + Decimal(delta)
    entry.save(update_fields=["amount"])
