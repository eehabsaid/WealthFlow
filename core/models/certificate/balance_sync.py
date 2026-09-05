from django.db.models.signals import post_save, post_delete, pre_save, pre_delete
from django.dispatch import receiver

from core.models.balance import BalanceEntry
from core.models.bank import Bank
from core.models.certificate.bank_certificate import BankCertificate


def _is_certificate_active(certificate):
    if certificate is None:
        return False

    status = str(getattr(certificate, "status", "") or "").strip().lower()
    return status == "active"


@receiver(pre_save, sender=BankCertificate, dispatch_uid="cbs_pre_save")
def handle_certificate_balance_pre_save(sender, instance, **kwargs):
    """Deducts the certificate principal from its matching cash balance
    entry. See core/services/certificate/certificate_balance_deduction_service.py
    for full behaviour notes. Does not affect the aggregate sync below."""
    from core.services.certificate.certificate_balance_deduction_service import (
        handle_certificate_pre_save,
    )
    handle_certificate_pre_save(sender, instance, **kwargs)


@receiver(post_save, sender=BankCertificate, dispatch_uid="cbs_post_save")
def handle_certificate_balance_post_save(sender, instance, created, **kwargs):
    from core.services.certificate.certificate_balance_deduction_service import (
        handle_certificate_post_save,
    )
    handle_certificate_post_save(sender, instance, created, **kwargs)


@receiver(pre_delete, sender=BankCertificate, dispatch_uid="cbs_pre_delete")
def handle_certificate_balance_pre_delete(sender, instance, **kwargs):
    from core.services.certificate.certificate_balance_deduction_service import (
        handle_certificate_pre_delete,
    )
    handle_certificate_pre_delete(sender, instance, **kwargs)


@receiver(post_save, sender=BankCertificate)
def handle_certificate_save(sender, instance, **kwargs):
    """
    Fires automatically on insert or update of a BankCertificate.
    Calculates total aggregate sum per bank and currency and updates BalanceEntry.
    """
    _sync_certificate_balance(instance.bank_id, instance.currency_id)


@receiver(post_delete, sender=BankCertificate)
def handle_certificate_delete(sender, instance, **kwargs):
    """
    Fires automatically when a BankCertificate is deleted.
    Recalculates balances to ensure zero values or removed allocations clear out.
    """
    _sync_certificate_balance(instance.bank_id, instance.currency_id)


def sync_certificate_balance_entries():
    for bank_id, currency_id in (
        BankCertificate.objects.exclude(bank_id__isnull=True, currency_id__isnull=True)
        .values_list("bank_id", "currency_id")
        .distinct()
    ):
        _sync_certificate_balance(bank_id, currency_id)

    for entry in BalanceEntry.objects.filter(balance_type="certificate"):
        if not entry.bank_id or not entry.currency_id:
            continue
        active_total = sum(
            float(c.amount or 0)
            for c in BankCertificate.objects.filter(
                bank_id=entry.bank_id,
                currency_id=entry.currency_id,
            )
            if _is_certificate_active(c)
        )
        entry.amount = active_total
        entry.save(update_fields=["amount"])


def _sync_certificate_balance(bank_id, currency_id):
    """
    Internal transactional helper to safely aggregate matching certificate fields
    and pipe them down to the parent Balance sheet.
    """
    if not bank_id or not currency_id:
        return

    certs = BankCertificate.objects.filter(bank_id=bank_id, currency_id=currency_id)
    total_amount = sum(
        float(c.amount or 0)
        for c in certs
        if _is_certificate_active(c)
    )

    if total_amount > 0:
        # Build standard engineering title syntax dynamically safely from foreign object tracking
        try:
            bank_instance = Bank.objects.get(pk=bank_id)
            title_text = f"{bank_instance.name} Certificates Balance"
        except Bank.DoesNotExist:
            title_text = "Certificates Balance"

        # Update matching row or build a clean new asset profile block automatically
        BalanceEntry.objects.update_or_create(
            balance_type="certificate",
            bank_id=bank_id,
            currency_id=currency_id,
            defaults={
                "title": title_text,
                "amount": total_amount,
                "notes": "Automated system synchronization from active bank certificates profile pipeline."
            }
        )
    else:
        # Cascade-delete or remove redundant balance references if aggregate returns empty sets
        BalanceEntry.objects.filter(
            balance_type="certificate",
            bank_id=bank_id,
            currency_id=currency_id
        ).delete()
