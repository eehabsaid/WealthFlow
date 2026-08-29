"""
Certificate -> Cash Balance principal deduction service.

NOTE (200-line file convention): this file is a standalone service kept
under the 200-line limit. If it grows past that, split it into a package
`core/services/certificate/balance_deduction/` with an `__init__.py` as
the single umbrella re-export source (see core/views/settings/__init__.py
for the documented convention), e.g.:
    balance_deduction/matching.py   - balance entry lookup helpers
    balance_deduction/signals.py    - pre_save / post_save / pre_delete handlers
    balance_deduction/errors.py     - exception classes

Behaviour (confirmed with product owner):
  1. Target balance entry is matched by bank_id + currency_id, restricted
     to BalanceEntry.balance_type == "cash" (case-insensitive: "cash",
     "Cash", "CASH", ... all match).
  2. If no matching cash balance entry exists for a certificate's
     bank/currency, saving the certificate is BLOCKED with
     CertificateBalanceMappingError (raised in pre_save, before any SQL
     write happens, so the certificate is never persisted).
  3. If the matching cash balance entry does not have enough funds to
     cover the certificate's principal, saving is BLOCKED with
     CertificateInsufficientBalanceError. On an update, the check is
     against the NET delta only: the old deduction (if it applies to the
     same bank/currency) is treated as already available again before
     checking whether the entry can cover the new amount. A pure status
     change or a decrease in amount can never trigger this error.
  4. On every save (create or update) the previous deduction (if any) is
     fully reversed and the current amount/bank/currency is re-deducted.
     This makes pure status changes (e.g. Active -> Closed) a no-op for
     the cash balance, while amount/bank/currency edits net out to the
     correct delta automatically. Deletion reverses the last-applied
     deduction.
  6. This does NOT touch or replace the existing certificate-aggregate
     sync in core/models/certificate.py (BalanceEntry balance_type
     "certificate"). That behaviour is untouched.
  7. The view layer (core/views/certificate_views.py) catches these two
     exceptions and returns a clean JSON 400 response of the form
     {"error_code": "...", "error": "<english fallback text>"} instead of
     letting them propagate as a raw 500. The frontend
     (static/js/bank_certificates/api.js) maps `error_code` to a
     translated message via t('error_' + error_code, ...), with the
     matching keys added to all four static/i18n/*.json files - fully
     supported by the i18n system, not hardcoded.
"""

from decimal import Decimal
import logging

from django.db import transaction
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# Old-value snapshot stashed on the instance between pre_save and post_save.
_SNAPSHOT_ATTR = "_cbs_old_snapshot"


class CertificateBalanceMappingError(ValidationError):
    """Raised when no matching cash BalanceEntry exists for a certificate's
    bank + currency. Subclasses ValidationError so it behaves like a normal
    Django validation failure if a caller chooses to catch it that way."""
    error_code = "certificate_balance_mapping_missing"


class CertificateInsufficientBalanceError(ValidationError):
    """Raised when the matching cash BalanceEntry does not have enough
    funds to cover the certificate's principal (net of any amount being
    freed up by reversing the certificate's previous deduction)."""
    error_code = "certificate_insufficient_balance"


def _cash_balance_queryset(bank_id, currency_id):
    from core.models import BalanceEntry

    return BalanceEntry.objects.filter(
        balance_type__iexact="cash",
        bank_id=bank_id,
        currency_id=currency_id,
    )


def find_cash_balance_entry(bank_id, currency_id, for_update=False):
    """Return the matching cash BalanceEntry for (bank_id, currency_id), or
    None. Logs a warning if more than one candidate row exists (ambiguous
    mapping); the lowest-id row is used deterministically."""
    qs = _cash_balance_queryset(bank_id, currency_id).order_by("id")
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


def validate_balance_entry_exists(bank_id, currency_id):
    """Raise CertificateBalanceMappingError if there is no cash BalanceEntry
    for this bank/currency pair. Called from pre_save so it blocks the
    certificate write entirely."""
    if find_cash_balance_entry(bank_id, currency_id) is None:
        raise CertificateBalanceMappingError(
            "There's no cash balance set up yet for this bank and currency. "
            "Please add one first, then save the certificate again."
        )


def validate_sufficient_balance(bank_id, currency_id, new_amount, old_snapshot):
    """Raise CertificateInsufficientBalanceError if the matching cash entry
    cannot cover `new_amount`. If `old_snapshot` (old_bank_id, old_currency_id,
    old_amount) applies to the SAME bank/currency as the new values, its
    amount is added back before checking - i.e. only the net delta must be
    covered. Assumes the matching entry already exists (call
    validate_balance_entry_exists first)."""
    entry = find_cash_balance_entry(bank_id, currency_id)
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


def _apply_delta(bank_id, currency_id, delta):
    """Add `delta` (Decimal, can be negative) to the matched cash balance
    entry's amount. No-op (with a warning) if no matching entry is found.
    Note: bank_id may legitimately be None (matches cash entries with no
    bank assigned) - only currency_id is required."""
    if currency_id is None or delta == 0:
        return
    entry = find_cash_balance_entry(bank_id, currency_id, for_update=True)
    if entry is None:
        logger.warning(
            "Cannot apply certificate balance delta: no cash BalanceEntry "
            "for bank_id=%s currency_id=%s", bank_id, currency_id,
        )
        return
    entry.amount = Decimal(entry.amount) + Decimal(delta)
    entry.save(update_fields=["amount"])


def handle_certificate_pre_save(sender, instance, **kwargs):
    """Validate the new bank/currency has a matching cash balance entry, and
    snapshot the pre-update values (if this is an update) for post_save."""
    old_snapshot = None
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            old_snapshot = (old.bank_id, old.currency_id, Decimal(old.amount))
        except sender.DoesNotExist:
            old_snapshot = None

    validate_balance_entry_exists(instance.bank_id, instance.currency_id)
    validate_sufficient_balance(
        instance.bank_id, instance.currency_id, instance.amount, old_snapshot,
    )
    setattr(instance, _SNAPSHOT_ATTR, old_snapshot)


def handle_certificate_post_save(sender, instance, created, **kwargs):
    """Reverse the previous deduction (if any) and apply the current one."""
    old_snapshot = getattr(instance, _SNAPSHOT_ATTR, None)
    with transaction.atomic():
        if old_snapshot is not None:
            old_bank_id, old_currency_id, old_amount = old_snapshot
            _apply_delta(old_bank_id, old_currency_id, old_amount)
        _apply_delta(instance.bank_id, instance.currency_id, -Decimal(instance.amount or 0))

    if hasattr(instance, _SNAPSHOT_ATTR):
        delattr(instance, _SNAPSHOT_ATTR)


def handle_certificate_pre_delete(sender, instance, **kwargs):
    """Reverse the certificate's currently-applied deduction before it is
    removed from the database."""
    with transaction.atomic():
        _apply_delta(instance.bank_id, instance.currency_id, Decimal(instance.amount or 0))
