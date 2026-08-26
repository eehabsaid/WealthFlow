from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class DateFormatterTest(TestCase):
    def test_format_date_languages(self):
        from core.utils.date_formatter import format_date
        d = date(2026, 7, 27)
        self.assertEqual(format_date(d, "en"), "27-Jul-2026")
        self.assertEqual(format_date(d, "fr"), "27-Juil.-2026")
        self.assertEqual(format_date(d, "ar"), "27-يوليو-2026")
        self.assertEqual(format_date(d, "de"), "27-Jul-2026")

        d_jan = date(2026, 1, 5)
        self.assertEqual(format_date(d_jan, "en"), "05-Jan-2026")
        self.assertEqual(format_date(d_jan, "fr"), "05-Janv.-2026")
        self.assertEqual(format_date(d_jan, "ar"), "05-يناير-2026")
        self.assertEqual(format_date(d_jan, "de"), "05-Jan-2026")

    def test_format_date_iso_and_time_preservation(self):
        from core.utils.date_formatter import format_date
        from datetime import datetime
        dt_obj = datetime(2026, 7, 27, 14, 35)
        self.assertEqual(format_date(dt_obj, "en"), "27-Jul-2026 14:35")

        
        iso_str = "2026-07-27"
        self.assertEqual(format_date(iso_str, "en"), "27-Jul-2026")

        iso_time_str = "2026-07-27 14:35"
        self.assertEqual(format_date(iso_time_str, "en"), "27-Jul-2026 14:35")

    def test_format_date_fallback(self):
        from core.utils.date_formatter import format_date
        self.assertEqual(format_date("invalid-date-string", "en"), "invalid-date-string")
        self.assertEqual(format_date("", "en"), "")
        self.assertEqual(format_date("-", "en"), "-")


class PerformanceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="perf_user",
            password="password123",
            is_active=True,
        )

    def test_performance_service_payload_structure(self):
        from core.services.financial_advisor.performance_service import PerformanceService
        svc = PerformanceService()
        payload = svc.payload()
        self.assertIn("gold", payload)
        self.assertIn("currencies", payload)
        self.assertIn("as_of", payload)
        self.assertIn("current_price_24k", payload["gold"])
        self.assertIn("exposure", payload["gold"])
        self.assertIn("rate_history_available", payload["currencies"])
        self.assertIn("data", payload["currencies"])
        self.assertIn("USD", payload["currencies"]["data"])
        self.assertIn("EUR", payload["currencies"]["data"])
        self.assertIn("SAR", payload["currencies"]["data"])

    def test_performance_service_empty_db_defensive(self):
        from core.services.financial_advisor.performance_service import PerformanceService
        from core.models import GoldPriceHistory, ExchangeRateHistory
        GoldPriceHistory.objects.all().delete()
        ExchangeRateHistory.objects.all().delete()

        svc = PerformanceService()
        payload = svc.payload()
        self.assertEqual(payload["gold"]["current_price_24k"], 0.0)
        self.assertEqual(payload["gold"]["exposure"]["gold_value"], 0.0)
        self.assertEqual(payload["gold"]["exposure"]["impact_7d"], 0.0)
        self.assertEqual(payload["gold"]["exposure"]["impact_30d"], 0.0)
        self.assertFalse(payload["currencies"]["rate_history_available"])

    def test_performance_view_unauthenticated(self):
        response = self.client.get("/api/financial-advisor/performance/")
        self.assertEqual(response.status_code, 401)

    def test_performance_view_authenticated(self):
        self.client.login(username="perf_user", password="password123")
        response = self.client.get("/api/financial-advisor/performance/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("gold", data)
        self.assertIn("currencies", data)
