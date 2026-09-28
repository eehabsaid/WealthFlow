"""Currency Analysis history must be expressed in the viewer's own default
currency, not the platform rate pivot the archive is stored against."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from core.models import AppSettings, ExchangeRateHistory
from core.services.exchange_rate_history_service import ExchangeRateHistoryService
from core.services.financial_advisor.performance_service import PerformanceService

User = get_user_model()
TODAY = date(2026, 9, 27)


def _row(code, day, mid):
    ExchangeRateHistory.objects.create(
        currency_code=code,
        buy_rate=Decimal(mid),
        sell_rate=Decimal(mid),
        mid_rate=Decimal(mid),
        fetched_at=timezone.now(),
        snapshot_date=day,
    )


class RebasedSeriesTests(TestCase):
    """ExchangeRateHistoryService.get_rate_series_in_base (pivot = EGP)."""

    def setUp(self):
        AppSettings.set("exchange_rate_pivot_code", "EGP")
        self.d1, self.d2 = TODAY - timedelta(days=2), TODAY - timedelta(days=1)
        for day, usd, sar in ((self.d1, "50", "13.333333"), (self.d2, "51", "13.6")):
            _row("USD", day, usd)
            _row("SAR", day, sar)
        self.svc = ExchangeRateHistoryService()

    def _series(self, code, base):
        return self.svc.get_rate_series_in_base(code, base, self.d1, TODAY)

    def test_pivot_base_is_identical_to_the_raw_archive(self):
        series, skipped = self._series("USD", "EGP")
        raw = list(self.svc.get_rate_range("USD", self.d1, TODAY))
        self.assertEqual(skipped, 0)
        self.assertEqual([r.snapshot_date for r in series], [r.snapshot_date for r in raw])
        self.assertEqual([r.mid_rate for r in series], [r.mid_rate for r in raw])

    def test_non_pivot_base_divides_same_day_rates(self):
        series, skipped = self._series("USD", "SAR")
        self.assertEqual(skipped, 0)
        self.assertEqual(series[0].mid_rate, (Decimal("50") / Decimal("13.333333")).quantize(Decimal("0.000001")))
        self.assertAlmostEqual(float(series[0].mid_rate), 3.75, places=3)
        self.assertAlmostEqual(float(series[1].mid_rate), 3.75, places=3)

    def test_pivot_currency_in_a_non_pivot_base(self):
        series, _ = self._series("EGP", "SAR")  # EGP has no archive rows
        self.assertEqual([r.snapshot_date for r in series], [self.d1, self.d2])
        self.assertAlmostEqual(float(series[0].mid_rate), 1 / 13.333333, places=5)

    def test_day_without_a_base_rate_is_skipped_and_counted(self):
        ExchangeRateHistory.objects.filter(currency_code="SAR", snapshot_date=self.d2).delete()
        series, skipped = self._series("USD", "SAR")
        self.assertEqual([r.snapshot_date for r in series], [self.d1])
        self.assertEqual(skipped, 1)

    def test_existing_history_queries_are_untouched(self):
        rows = list(self.svc.get_rate_range("USD", self.d1, TODAY))
        self.assertEqual([r.mid_rate for r in rows], [Decimal("50.000000"), Decimal("51.000000")])
        self.assertEqual(self.svc.get_rate_on_date("USD", self.d1).mid_rate, Decimal("50.000000"))


class PerformancePayloadBaseTests(TestCase):
    """PerformanceService.payload()['currencies'] per viewer base currency."""

    def setUp(self):
        AppSettings.set("exchange_rate_pivot_code", "EGP")
        for i in range(3):
            day = TODAY - timedelta(days=i)
            _row("USD", day, "50")
            _row("EUR", day, "58")
            _row("SAR", day, "13.333333")
        from core.models import ExchangeRate

        for code, rate in (("USD", "50"), ("EUR", "58"), ("SAR", "13.333333")):
            ExchangeRate.objects.create(
                currency_code=code, buy_rate=Decimal(rate), sell_rate=Decimal(rate), mid_rate=Decimal(rate)
            )

    def _payload(self, username, base):
        user = User.objects.create_user(username=username, password="pw12345")
        user.profile.preferred_currency = base
        user.profile.save()
        return PerformanceService(user, today=TODAY).payload()["currencies"]

    def test_pivot_base_user_sees_the_same_three_tabs_and_raw_values(self):
        cur = self._payload("egp_viewer", "EGP")
        self.assertEqual(cur["codes"], ["USD", "EUR", "SAR"])
        self.assertEqual(cur["base_code"], "EGP")
        self.assertEqual(cur["data"]["USD"]["current_rate"], 50.0)
        self.assertEqual({p["mid_rate"] for p in cur["data"]["USD"]["timeseries"]}, {50.0})

    def test_sar_base_user_sees_usd_in_sar_and_egp_replaces_the_base_tab(self):
        cur = self._payload("sar_viewer", "SAR")
        self.assertEqual(cur["codes"], ["USD", "EUR", "EGP"])
        self.assertAlmostEqual(cur["data"]["USD"]["current_rate"], 3.75, places=2)
        self.assertAlmostEqual(cur["data"]["EUR"]["current_rate"], 4.35, places=2)
        self.assertAlmostEqual(cur["data"]["EGP"]["current_rate"], 0.075, places=3)

    def test_payload_endpoint_returns_rebased_values_over_http(self):
        user = User.objects.create_user(username="sar_http", password="pw12345")
        user.profile.preferred_currency = "SAR"
        user.profile.save()
        client = Client()
        client.force_login(user)
        res = client.get("/api/financial-advisor/performance/")
        self.assertEqual(res.status_code, 200)
        usd = res.json()["currencies"]["data"]["USD"]
        self.assertAlmostEqual(usd["timeseries"][-1]["mid_rate"], 3.75, places=2)
