"""pre_save / post_save / pre_delete handlers (wired in
core/models/certificate/balance_sync.py)."""

from django.db import transaction

from .matching import (
    apply_delta,
    held_amount,
    validate_balance_entry_exists,
    validate_sufficient_balance,
)

# Old-value snapshot stashed on the instance between pre_save and post_save.
_SNAPSHOT_ATTR = "_cbs_old_snapshot"


def handle_certificate_pre_save(sender, instance, **kwargs):
    """Validate the new bank/currency has a matching cash balance entry and
    can cover the principal that will be held, and snapshot the pre-update
    held principal (if this is an update) for post_save."""
    old_snapshot = None
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            old_snapshot = (
                old.bank_id, old.currency_id, held_amount(old.amount, old.status),
            )
        except sender.DoesNotExist:
            old_snapshot = None

    validate_balance_entry_exists(instance.bank_id, instance.currency_id, instance.owner)
    validate_sufficient_balance(
        instance.bank_id, instance.currency_id,
        held_amount(instance.amount, instance.status), old_snapshot, instance.owner,
    )
    setattr(instance, _SNAPSHOT_ATTR, old_snapshot)


def handle_certificate_post_save(sender, instance, created, **kwargs):
    """Reverse the previously held principal (if any) and hold the current
    one. Closing releases the principal back to cash; re-opening holds it
    again."""
    old_snapshot = getattr(instance, _SNAPSHOT_ATTR, None)
    with transaction.atomic():
        if old_snapshot is not None:
            old_bank_id, old_currency_id, old_held = old_snapshot
            apply_delta(old_bank_id, old_currency_id, old_held, instance.owner)
        apply_delta(
            instance.bank_id, instance.currency_id,
            -held_amount(instance.amount, instance.status), instance.owner,
        )

    if hasattr(instance, _SNAPSHOT_ATTR):
        delattr(instance, _SNAPSHOT_ATTR)


def handle_certificate_pre_delete(sender, instance, **kwargs):
    """Reverse the certificate's currently-held principal (none if it is
    already closed) before it is removed from the database."""
    with transaction.atomic():
        apply_delta(
            instance.bank_id, instance.currency_id,
            held_amount(instance.amount, instance.status), instance.owner,
        )
