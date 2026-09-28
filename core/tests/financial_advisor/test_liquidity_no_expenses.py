from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import BalanceEntry, Currency

User = get_user_model()



class LiquidityNoExpensesHttpTest(TestCase):
    """Cash but no expenses must never read as a healthy / 12-month emergency fund."""

    def setUp(self):
        self.egp = Currency.objects.get_or_create(
            code="EGP", defaults={"symbol": "£", "name": "Egyptian Pound"})[0]
        self.user = User.objects.create_user(username="cash_only", password="pass12345")
        BalanceEntry.objects.create(owner=self.user, title="Wallet", balance_type="cash",
                                    currency=self.egp, amount=50000)
        self.client.login(username="cash_only", password="pass12345")

    def _get(self, name):
        resp = self.client.get(f"/api/financial-advisor/{name}/")
        self.assertEqual(resp.status_code, 200)
        return resp.json()

    def test_portfolio_optimizer_reports_no_coverage(self):
        self.assertIsNone(self._get("portfolio-optimizer")["expense_baseline"]["emergency_fund_months"])

    def test_risk_analysis_is_neutral_not_excellent(self):
        payload = self._get("risk-analysis")
        text = str(payload)
        self.assertNotIn("risk_analysis_reason_liq_good", text)
        self.assertNotIn("risk_analysis_finding_liquidity_good_title", text)
        self.assertIn("risk_analysis_reason_liq_no_data", text)
        self.assertIn("risk_analysis_finding_liquidity_no_data_title", text)

    def test_overview_stays_neutral(self):
        payload = self._get("overview")
        self.assertIsNone(payload["executive_summary"]["emergency_months"])
        self.assertEqual(payload["executive_summary"]["liquidity_status_key"], "overview_liquidity_no_data")
        keys = [a["title_key"] for a in payload["alerts"]]
        self.assertNotIn("overview_alert_emergency_fund_healthy_title", keys)
