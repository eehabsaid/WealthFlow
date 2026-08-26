from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

User = get_user_model()


class ExchangeRateArchiveTest(TestCase):
    def setUp(self):
        from core.models import ExchangeRate
        # Create two current rates with known fetched_at timestamps
        self.usd = ExchangeRate.objects.create(
            currency_code="USD",
            currency_name="US Dollar",
            buy_rate=Decimal("49.500000"),
            sell_rate=Decimal("50.500000"),
            mid_rate=Decimal("50.000000"),
            source="open.er-api.com",
        )
        self.eur = ExchangeRate.objects.create(
            currency_code="EUR",
            currency_name="Euro",
            buy_rate=Decimal("53.900000"),
            sell_rate=Decimal("54.100000"),
            mid_rate=Decimal("54.000000"),
            source="open.er-api.com",
        )

    def test_archive_inserts_rows_into_history(self):
        from core.models import ExchangeRateHistory
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService

        inserted = ExchangeRateHistoryService().archive_current_rates()
        self.assertEqual(inserted, 2)
        self.assertEqual(ExchangeRateHistory.objects.count(), 2)

    def test_archive_snapshot_date_derived_from_fetched_at(self):
        """snapshot_date must come from ExchangeRate.fetched_at, not today."""
        from core.models import ExchangeRateHistory
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService

        ExchangeRateHistoryService().archive_current_rates()

        usd_history = ExchangeRateHistory.objects.get(currency_code="USD")
        expected_date = self.usd.fetched_at.astimezone(__import__("datetime").timezone.utc).date()
        self.assertEqual(usd_history.snapshot_date, expected_date)

    def test_archive_preserves_decimal_precision(self):
        """Rates must remain Decimal — not rounded via float."""
        from core.models import ExchangeRateHistory
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService

        ExchangeRateHistoryService().archive_current_rates()

        row = ExchangeRateHistory.objects.get(currency_code="USD")
        self.assertIsInstance(row.mid_rate, Decimal)
        self.assertEqual(row.mid_rate, Decimal("50.000000"))

    def test_archive_duplicate_same_day_skipped(self):
        """Running archive twice on the same day must not create duplicate rows."""
        from core.models import ExchangeRateHistory
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService

        svc = ExchangeRateHistoryService()
        svc.archive_current_rates()
        # Second call — same date, same mid_rate: should not insert again
        inserted_second = svc.archive_current_rates()
        self.assertEqual(inserted_second, 0)
        self.assertEqual(ExchangeRateHistory.objects.count(), 2)

    def test_archive_archives_daily_snapshot_regardless_of_mid_rate_change(self):
        """One snapshot per currency per day is archived regardless of rate changes."""
        from core.models import ExchangeRate, ExchangeRateHistory
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService

        svc = ExchangeRateHistoryService()
        # First archive — both inserted
        svc.archive_current_rates()
        self.assertEqual(ExchangeRateHistory.objects.count(), 2)

        # Update fetched_at to simulate a new day
        tomorrow = timezone.now() + timedelta(days=1)
        ExchangeRate.objects.all().update(fetched_at=tomorrow)

        # Second archive on a new day — both inserted even though rates did not change
        inserted = svc.archive_current_rates()
        self.assertEqual(inserted, 2)
        self.assertEqual(ExchangeRateHistory.objects.count(), 4)

    def test_archive_failure_does_not_raise(self):
        """
        If archive_current_rates encounters an internal error, it must
        log it and return 0 — never raise — so the refresh can continue.
        """
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService
        from unittest.mock import patch

        svc = ExchangeRateHistoryService()
        with patch.object(svc, "_archive_current_rates_inner", side_effect=RuntimeError("DB exploded")):
            result = svc.archive_current_rates()
        self.assertEqual(result, 0)

    def test_archive_empty_table_returns_zero(self):
        """Archive on empty core_exchangerate should return 0 without error."""
        from core.models import ExchangeRate
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService

        ExchangeRate.objects.all().delete()
        inserted = ExchangeRateHistoryService().archive_current_rates()
        self.assertEqual(inserted, 0)
