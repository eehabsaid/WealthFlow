from django.db import models
from django.db.models import Case, Value, When
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from datetime import date, datetime

from .bank import Bank
from .currency import Currency
from .balance import BalanceEntry

def _is_certificate_active(certificate):
    if certificate is None:
        return False

    status = str(getattr(certificate, "status", "") or "").strip().lower()
    return status == "active"


class BankCertificate(models.Model):
    bank = models.ForeignKey(
        Bank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="certificates",
    )
    currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, null=True, blank=True
    )
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    interest_rate = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    interest_value = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    frequency = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=50, default="Active", blank=True)
    last_interest_posted_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            Case(
                When(status__iexact="closed", then=Value(1)),
                default=Value(0),
                output_field=models.IntegerField(),
            ),
            "issue_date__day",
            "bank__name",
        ]

    def to_dict(self):
        return {
            "id": self.id,
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "currency_id": self.currency_id,
            "currency_code": self.currency.code if self.currency else "",
            "currency_symbol": self.currency.symbol if self.currency else "",
            "currency_flag": self.currency.flag if self.currency else "💱",
            "issue_date": (
                self.issue_date.isoformat()
                if isinstance(self.issue_date, (date, datetime))
                else (self.issue_date or "")
            ),
            "expiry_date": (
                self.expiry_date.isoformat()
                if isinstance(self.expiry_date, (date, datetime))
                else (self.expiry_date or "")
            ),
            "amount": float(self.amount),
            "interest_rate": float(self.interest_rate),
            "interest_value": float(self.interest_value),
            "frequency": self.frequency,
            "status": self.status,
            "last_interest_posted_date": (
                self.last_interest_posted_date.isoformat()
                if isinstance(self.last_interest_posted_date, (date, datetime))
                else (self.last_interest_posted_date or "")
            ),
            "notes": self.notes,
        }

    def __str__(self):
        bank_name = self.bank.name if self.bank else "Unknown Bank"
        return f"{bank_name} Certificate {self.id}"


class BankCertificateInterestHistory(models.Model):
    certificate = models.ForeignKey(
        BankCertificate,
        on_delete=models.CASCADE,
        related_name="interest_history",
    )
    posting_date = models.DateField()
    posting_period = models.CharField(max_length=50)
    interest_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["posting_date", "id"]
        unique_together = ["certificate", "posting_date"]

    def to_dict(self):
        return {
            "id": self.id,
            "certificate_id": self.certificate_id,
            "posting_date": self.posting_date.isoformat() if self.posting_date else "",
            "posting_period": self.posting_period,
            "interest_amount": float(self.interest_amount or 0),
            "bank_id": self.bank_id,
            "bank_name": self.bank.name if self.bank else "",
            "currency_id": self.currency_id,
            "currency_code": self.currency.code if self.currency else "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


class CertificateStatus(models.Model):
    """Admin-configurable certificate lifecycle statuses."""

    name = models.CharField(max_length=100, unique=True)
    color_hex = models.CharField(max_length=7, default="#1a6ef5")
    is_default = models.BooleanField(
        default=False, help_text="Used as default status for new certs"
    )
    is_terminal = models.BooleanField(
        default=False, help_text="No further renewals expected"
    )
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "color_hex": self.color_hex,
            "is_default": self.is_default,
            "is_terminal": self.is_terminal,
            "order": self.order,
        }

    def __str__(self):
        return self.name


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
