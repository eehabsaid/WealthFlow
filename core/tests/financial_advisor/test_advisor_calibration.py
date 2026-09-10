from core.models import ExchangeRate
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import BalanceEntry, Bank, Currency, Expense

User = get_user_model()


class FinancialIntelligenceCalibrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser_calib", password="pass12345")
        self.client.force_login(self.user)
        self.egp = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.usd = Currency.objects.create(code="USD", symbol="$", name="US Dollar")
        self.gold = Currency.objects.create(code="GOLD", symbol="g", name="Gold")

    def test_liquidity_uses_cash_entries_and_buy_rate_only(self):
        ExchangeRate.objects.create(currency_code="USD", buy_rate=50, sell_rate=55)

        BalanceEntry.objects.create(
            owner=self.user,
            title="Home Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.egp,
            amount=1000,
        )
        BalanceEntry.objects.create(
            owner=self.user,
            title="USD Wallet",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.usd,
            amount=10,
        )
        BalanceEntry.objects.create(
            owner=self.user,
            title="Gold Grams",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.gold,
            amount=5,
        )
        BalanceEntry.objects.create(
            owner=self.user,
            title="Bank Account",
            balance_type=BalanceEntry.BalanceType.BANK,
            currency=self.egp,
            amount=999999,
        )

        response = self.client.get("/api/certificate-forecast/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        # 1000 EGP + (10 USD * 50 buy rate). Gold and BANK rows are excluded.
        self.assertEqual(payload["cash_balance"], 1500.0)

    def test_low_liquidity_recommendation_requires_real_liquidity_pressure(self):
        BalanceEntry.objects.create(
            owner=self.user,
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.egp,
            amount=100000,
        )
        Expense.objects.create(
            owner=self.user,
            date=date(2026, 6, 1),
            year=2026,
            month=6,
            amount=1000,
            amount_egp=1000,
        )

        healthy = self.client.get("/api/certificate-forecast/")
        self.assertEqual(healthy.status_code, 200)
        healthy_recs = healthy.json().get("financial_recommendations") or []
        self.assertNotIn("recommend_low_liquidity", healthy_recs)

        BalanceEntry.objects.all().delete()
        Expense.objects.all().delete()

        BalanceEntry.objects.create(
            owner=self.user,
            title="Small Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.egp,
            amount=1000,
        )
        Expense.objects.create(owner=self.user, date=date(2026, 5, 1), year=2026, month=5, amount=20000, amount_egp=20000)
        Expense.objects.create(owner=self.user, date=date(2026, 6, 1), year=2026, month=6, amount=18000, amount_egp=18000)
        Expense.objects.create(owner=self.user, date=date(2026, 7, 1), year=2026, month=7, amount=22000, amount_egp=22000)

        stressed = self.client.get("/api/certificate-forecast/")
        self.assertEqual(stressed.status_code, 200)
        stressed_recs = stressed.json().get("financial_recommendations") or []
        self.assertIn("recommend_low_liquidity", stressed_recs)

    def test_recommended_action_is_never_empty(self):
        response = self.client.get("/api/certificate-forecast/")
        self.assertEqual(response.status_code, 200)
        action = response.json().get("action_plan") or {}

        self.assertIsInstance(action, dict)
        self.assertTrue(action.get("key"))

    def test_balance_summary_liquid_egp_cash_uses_cash_egp_rows_only(self):
        bank = Bank.objects.create(name="CIB", owner=self.user)
        cash_currency = Currency.objects.create(code="cash", symbol="c", name="Cash")

        BalanceEntry.objects.create(
            owner=self.user,
            title="Home EGP Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.egp,
            amount=1000,
        )
        BalanceEntry.objects.create(
            owner=self.user,
            title="Bank EGP Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=bank,
            currency=self.egp,
            amount=2500,
        )
        BalanceEntry.objects.create(
            owner=self.user,
            title="Cash Currency",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=cash_currency,
            amount=9999,
        )
        BalanceEntry.objects.create(
            owner=self.user,
            title="EGP Bank Type",
            balance_type=BalanceEntry.BalanceType.BANK,
            currency=self.egp,
            amount=7777,
        )

        response = self.client.get("/api/balance/")
        self.assertEqual(response.status_code, 200)
        summary = response.json().get("summary") or {}

        self.assertEqual(summary.get("liquid_egp_cash"), 3500.0)
