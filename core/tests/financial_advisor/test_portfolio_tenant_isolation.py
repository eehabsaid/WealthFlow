from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import BalanceEntry, Bank, Currency
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.risk_analysis_service import RiskAnalysisService

User = get_user_model()


class PortfolioRiskTenantIsolationTest(TestCase):
    """A brand-new user must not see another user's banks/balances."""

    def setUp(self):
        self.owner_a = User.objects.create_user(username="tenant_a", password="pass12345")
        self.owner_b = User.objects.create_user(username="tenant_b_empty", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        bank = Bank.objects.create(owner=self.owner_a, name="QNB")
        BalanceEntry.objects.create(
            owner=self.owner_a,
            title="QNB Balance",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=bank,
            currency=self.egp,
            amount=100000,
        )

    def test_empty_user_has_no_bank_or_balance_exposure(self):
        svc = PortfolioOptimizerService(self.owner_b, today=date(2026, 9, 20))
        comp = svc.net_worth.portfolio_components()
        self.assertEqual(svc._bank_exposure(comp), [])
        self.assertEqual(svc._largest_balance_entry(comp)["title"], "-")

    def test_owner_still_sees_own_exposure(self):
        svc = PortfolioOptimizerService(self.owner_a, today=date(2026, 9, 20))
        comp = svc.net_worth.portfolio_components()
        self.assertEqual(svc._bank_exposure(comp)[0]["bank_name"], "QNB")
        self.assertEqual(svc._largest_balance_entry(comp)["title"], "QNB Balance")

    def test_risk_analysis_empty_user_has_no_bank_finding(self):
        payload = RiskAnalysisService(self.owner_b, today=date(2026, 9, 20)).payload()
        self.assertNotIn("QNB", str(payload))
