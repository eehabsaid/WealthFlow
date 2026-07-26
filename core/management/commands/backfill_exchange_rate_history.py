"""
Management command: backfill_exchange_rate_history

Imports historical daily exchange-rate snapshots for the past N days
into core_exchangeratehistory using ExchangeRateHistoryService.

Usage:
    python manage.py backfill_exchange_rate_history
    python manage.py backfill_exchange_rate_history --days 180
    python manage.py backfill_exchange_rate_history --days 30

The command is idempotent; re-running skips rows already in the DB.
"""

import json

from django.core.management.base import BaseCommand

from core.services.exchange_rate_history_service import ExchangeRateHistoryService


class Command(BaseCommand):
    help = "Backfill historical exchange-rate snapshots into core_exchangeratehistory"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=180,
            help="Number of past days to backfill (default: 180).",
        )

    def handle(self, *args, **options):
        days = options["days"]
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Backfilling exchange rate history for the past {days} days ..."
            )
        )
        self.stdout.write(
            "  Provider: Yahoo Finance (yfinance batch API, free public data)"
        )
        self.stdout.write(
            "  Duplicate rows will be skipped automatically.\n"
        )

        result = ExchangeRateHistoryService().import_historical_rates(days=days)

        self.stdout.write(json.dumps(result, indent=2))

        if result["gaps"] > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n  {result['gaps']} day(s) had no data from provider "
                    "(gaps recorded in log). No data was fabricated."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. imported={result['imported']}, "
                f"skipped={result['skipped']}, "
                f"gaps={result['gaps']}."
            )
        )
