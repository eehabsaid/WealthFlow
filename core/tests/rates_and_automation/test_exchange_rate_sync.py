from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class ExchangeRateSyncTest(TestCase):
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

    def test_import_historical_rates_uses_injected_provider(self):
        """Provider injection must work; rows are bulk-created correctly."""
        from core.models import ExchangeRateHistory
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService
        from core.integrations.historical_exchange_rate_provider import (
            BaseHistoricalRateProvider, HistoricalRateRecord,
        )
        from datetime import date

        class FakeProvider(BaseHistoricalRateProvider):
            SOURCE_NAME = "fake"

            def fetch_date(self, target_date: date):
                return [
                    HistoricalRateRecord(
                        currency_code="USD",
                        currency_name="US Dollar",
                        buy_rate=Decimal("49.000000"),
                        sell_rate=Decimal("51.000000"),
                        mid_rate=Decimal("50.000000"),
                        source="fake",
                        snapshot_date=target_date,
                    )
                ]

        result = ExchangeRateHistoryService().import_historical_rates(
            days=3, provider=FakeProvider()
        )
        self.assertEqual(result["imported"], 3)
        self.assertEqual(result["gaps"], 0)
        self.assertEqual(ExchangeRateHistory.objects.count(), 3)

    def test_import_historical_rates_skips_existing_rows(self):
        """Re-running import must not duplicate existing rows."""
        from core.models import ExchangeRateHistory
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService
        from core.integrations.historical_exchange_rate_provider import (
            BaseHistoricalRateProvider, HistoricalRateRecord,
        )
        from datetime import date

        class FakeProvider(BaseHistoricalRateProvider):
            SOURCE_NAME = "fake"

            def fetch_date(self, target_date: date):
                return [
                    HistoricalRateRecord(
                        currency_code="USD", currency_name="US Dollar",
                        buy_rate=Decimal("49"), sell_rate=Decimal("51"),
                        mid_rate=Decimal("50"), source="fake",
                        snapshot_date=target_date,
                    )
                ]

        svc = ExchangeRateHistoryService()
        first = svc.import_historical_rates(days=2, provider=FakeProvider())
        second = svc.import_historical_rates(days=2, provider=FakeProvider())

        self.assertEqual(first["imported"], 2)
        self.assertEqual(second["imported"], 0)
        self.assertEqual(second["skipped"], 2)
        self.assertEqual(ExchangeRateHistory.objects.count(), 2)

    def test_import_historical_rates_handles_provider_gaps(self):
        """Days where provider returns empty list are counted as gaps."""
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService
        from core.integrations.historical_exchange_rate_provider import (
            BaseHistoricalRateProvider,
        )
        from datetime import date

        class EmptyProvider(BaseHistoricalRateProvider):
            SOURCE_NAME = "empty"

            def fetch_date(self, target_date: date):
                return []

        result = ExchangeRateHistoryService().import_historical_rates(
            days=3, provider=EmptyProvider()
        )
        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["gaps"], 3)

    def test_refresh_latest_rates_archives_before_overwrite(self):
        """
        Smoke test: calling ExchangeRateService.refresh_latest_rates()
        with a mocked fetch must archive the pre-existing rates into history.
        """
        from core.models import ExchangeRate, ExchangeRateHistory
        from core.services.shared.exchange_rate_service import ExchangeRateService
        from unittest.mock import patch

        # Pre-condition: 2 rates exist (from setUp)
        self.assertEqual(ExchangeRate.objects.count(), 2)

        fake_raw = {
            "USD": 0.02,  # 1 / 0.02 = 50 EGP per USD
            "EUR": 0.018519,
        }
        with patch(
            "core.integrations.fetch_latest_exchange_rates",
            return_value=fake_raw,
        ):
            ExchangeRateService().refresh_latest_rates()

        # Archive should have captured the old 2 rows
        self.assertGreaterEqual(ExchangeRateHistory.objects.count(), 1)
        # Current table should still be populated (refresh succeeded)
        self.assertGreater(ExchangeRate.objects.count(), 0)

    def test_refresh_does_not_block_when_archive_fails(self):
        """
        If archive_current_rates() raises internally, refresh must still
        complete and current rates must still be updated.
        """
        from core.models import ExchangeRate
        from core.services.shared.exchange_rate_service import ExchangeRateService
        from unittest.mock import patch

        fake_raw = {"USD": 0.02}
        with patch(
            "core.integrations.fetch_latest_exchange_rates",
            return_value=fake_raw,
        ), patch(
            "core.services.exchange_rate_history_service.ExchangeRateHistoryService._archive_current_rates_inner",
            side_effect=Exception("archive boom"),
        ):
            result = ExchangeRateService().refresh_latest_rates()

        # Refresh must have completed despite archive error
        self.assertGreater(result.saved, 0)
        self.assertGreater(ExchangeRate.objects.count(), 0)
