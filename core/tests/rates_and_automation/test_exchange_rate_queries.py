from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class ExchangeRateQueriesTest(TestCase):
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

    def test_get_rate_on_date_returns_correct_row(self):
        from core.models import ExchangeRateHistory
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService
        from datetime import date
        from django.utils import timezone as tz

        today = date.today()
        ExchangeRateHistory.objects.create(
            currency_code="USD",
            currency_name="US Dollar",
            buy_rate=Decimal("49.000000"),
            sell_rate=Decimal("51.000000"),
            mid_rate=Decimal("50.000000"),
            source="test",
            fetched_at=tz.now(),
            snapshot_date=today,
        )

        svc = ExchangeRateHistoryService()
        row = svc.get_rate_on_date("USD", today)
        self.assertIsNotNone(row)
        self.assertEqual(row.mid_rate, Decimal("50.000000"))

    def test_get_rate_on_date_returns_none_for_missing(self):
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService
        from datetime import date

        row = ExchangeRateHistoryService().get_rate_on_date("XYZ", date(2020, 1, 1))
        self.assertIsNone(row)

    def test_get_rate_range_returns_ordered_queryset(self):
        from core.models import ExchangeRateHistory
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService
        from datetime import date
        from django.utils import timezone as tz

        base = date(2026, 1, 1)
        for i in range(5):
            snap = base + timedelta(days=i)
            ExchangeRateHistory.objects.create(
                currency_code="USD",
                currency_name="US Dollar",
                buy_rate=Decimal("49.000000"),
                sell_rate=Decimal("51.000000"),
                mid_rate=Decimal(str(50 + i)),
                source="test",
                fetched_at=tz.now(),
                snapshot_date=snap,
            )

        svc = ExchangeRateHistoryService()
        qs = svc.get_rate_range("USD", date(2026, 1, 2), date(2026, 1, 4))
        dates = list(qs.values_list("snapshot_date", flat=True))
        self.assertEqual(len(dates), 3)
        self.assertEqual(dates, sorted(dates))  # ascending order

    def test_get_rate_range_excludes_other_currencies(self):
        from core.models import ExchangeRateHistory
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService
        from datetime import date
        from django.utils import timezone as tz

        snap = date(2026, 3, 1)
        ExchangeRateHistory.objects.create(
            currency_code="USD", currency_name="US Dollar",
            buy_rate=Decimal("49"), sell_rate=Decimal("51"),
            mid_rate=Decimal("50"), source="test",
            fetched_at=tz.now(), snapshot_date=snap,
        )
        ExchangeRateHistory.objects.create(
            currency_code="EUR", currency_name="Euro",
            buy_rate=Decimal("53"), sell_rate=Decimal("55"),
            mid_rate=Decimal("54"), source="test",
            fetched_at=tz.now(), snapshot_date=snap,
        )

        qs = ExchangeRateHistoryService().get_rate_range("USD", snap, snap)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().currency_code, "USD")
