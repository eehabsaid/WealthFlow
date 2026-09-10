"""
Management command: backfill_owners

Assigns a single owner to every pre-existing row across the 14 root
models that just gained an `owner` FK (Bank, Company, ExpenseCategory,
Expense, Goal, Scenario, ReminderRule, BankCertificate, BalanceEntry,
BalanceTransfer, CreditCardPayment, CardRenewalFee, BankInterest,
FixedAsset), plus CurrencyExchange's pre-existing `user` field.

This is intentionally a separate, explicit step from `migrate` — the
schema migration only adds the (nullable) column; this command performs
the one-time data backfill and must be run once, by hand, after
`migrate`, before real multi-user usage begins.

Usage:
    python manage.py backfill_owners --username eehabsaid
    python manage.py backfill_owners --username eehabsaid --dry-run

Idempotent: only rows where owner is currently NULL are touched, so
re-running is safe and a no-op once everything is backfilled.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import (
    Bank,
    Company,
    ExpenseCategory,
    Expense,
    Goal,
    Scenario,
    ReminderRule,
    BankCertificate,
    BalanceEntry,
    BalanceTransfer,
    CreditCardPayment,
    CardRenewalFee,
    BankInterest,
    FixedAsset,
    CurrencyExchange,
)

OWNER_FIELD_MODELS = [
    Bank,
    Company,
    ExpenseCategory,
    Expense,
    Goal,
    Scenario,
    ReminderRule,
    BankCertificate,
    BalanceEntry,
    BalanceTransfer,
    CreditCardPayment,
    CardRenewalFee,
    BankInterest,
    FixedAsset,
]


class Command(BaseCommand):
    help = "Backfill owner on all pre-existing rows to a single user, one time, after migrate."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            required=True,
            help="Username of the account that should own all pre-existing data.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report counts without writing any changes.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        dry_run = options["dry_run"]

        try:
            owner = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"No user found with username '{username}'")

        self.stdout.write(f"Backfilling owner -> {owner.username} (id={owner.id})")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be written"))

        total = 0
        with transaction.atomic():
            for model in OWNER_FIELD_MODELS:
                qs = model.objects.filter(owner__isnull=True)
                count = qs.count()
                total += count
                if count:
                    self.stdout.write(f"  {model.__name__}: {count} row(s)")
                    if not dry_run:
                        qs.update(owner=owner)

            ce_qs = CurrencyExchange.objects.filter(user__isnull=True)
            ce_count = ce_qs.count()
            total += ce_count
            if ce_count:
                self.stdout.write(f"  CurrencyExchange (user field): {ce_count} row(s)")
                if not dry_run:
                    ce_qs.update(user=owner)

            if dry_run:
                transaction.set_rollback(True)

        if total == 0:
            self.stdout.write(self.style.SUCCESS("Nothing to backfill — all rows already have an owner."))
        elif dry_run:
            self.stdout.write(self.style.WARNING(f"Would backfill {total} row(s) total. Re-run without --dry-run to apply."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Backfilled {total} row(s) total to owner '{owner.username}'."))
