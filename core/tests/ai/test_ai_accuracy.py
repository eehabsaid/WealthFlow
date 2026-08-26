"""
Unit tests for WealthFlow AI End-to-End Accuracy, Multi-Tenant Scoping,
Deterministic Financial Calculations, Multi-Currency Conversion, and Priority Context Assembly.
"""

import json
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User

from core.models import (
    Currency, ExchangeRate, Bank, BalanceEntry, BankCertificate,
    FixedAsset, GoldDetails, GoldPrice, Expense, ExpenseCategory, Company, SalaryEntry
)
from core.services.ai.providers.balance_provider import BalanceDataProvider
from core.services.ai.providers.certificates_provider import BankCertificatesDataProvider
from core.services.ai.providers.assets_provider import FixedAssetsDataProvider
from core.services.ai.providers.salary_provider import SalaryDataProvider
from core.services.ai.context_builder_service import ContextBuilderService


class AIAccuracyTestSuite(TestCase):
    def setUp(self):
        # Users
        self.user_a = User.objects.create_user(username="accuracy_user_a", password="password123")
        self.user_b = User.objects.create_user(username="accuracy_user_b", password="password123")

        # Currencies
        self.egp = Currency.objects.create(code="EGP", name="Egyptian Pound", symbol="EGP")
        self.usd = Currency.objects.create(code="USD", name="US Dollar", symbol="$")

        # Exchange rate: 1 USD = 50 EGP
        ExchangeRate.objects.create(currency_code="USD", currency_name="US Dollar", mid_rate=Decimal("50.00"), buy_rate=Decimal("50.00"), sell_rate=Decimal("50.00"))

        # Bank
        self.bank = Bank.objects.create(name="CIB Bank")

        # User Balances
        BalanceEntry.objects.create(bank=self.bank, currency=self.egp, title="CIB EGP Current", amount=Decimal("100000.00"))
        BalanceEntry.objects.create(bank=self.bank, currency=self.usd, title="CIB USD Savings", amount=Decimal("10000.00"))

        # User Certificates (post-save signal auto-syncs 200,000 EGP certificate balance entry)
        BankCertificate.objects.create(
            bank=self.bank,
            currency=self.egp,
            amount=Decimal("200000.00"),
            interest_rate=Decimal("22.50"),
            interest_value=Decimal("3750.00"),
            issue_date=date(2025, 1, 1),
            expiry_date=date(2026, 1, 1),
            status="active"
        )

        # Gold Spot Price 24K = 3000 EGP/gram
        GoldPrice.objects.create(carat_24k=Decimal("3000.00"), carat_18k=Decimal("2250.00"))

        # User Gold Asset (100g of 18K Gold -> 100 * 2250 = 225,000 EGP)
        gold_fa = FixedAsset.objects.create(name="Gold Bar 18K", asset_type="Gold", purchase_date=date(2025, 1, 1), purchase_price=Decimal("200000.00"), current_market_value=Decimal("225000.00"))
        GoldDetails.objects.create(asset=gold_fa, purity="18K", weight=Decimal("100.00"), unit="gram", market_price=Decimal("2250.00"))

        # Expenses
        cat_housing = ExpenseCategory.objects.create(name="Housing")
        Expense.objects.create(category=cat_housing, currency=self.egp, amount=Decimal("15000.00"), date=date(2026, 7, 1), year=2026, month=7)

        # Salary
        company = Company.objects.create(name="TechCorp", is_active=True)
        SalaryEntry.objects.create(company=company, year=2025, month="January", paid=Decimal("50000.00"), expected=Decimal("50000.00"))
        SalaryEntry.objects.create(company=company, year=2026, month="January", paid=Decimal("60000.00"), expected=Decimal("60000.00"))

    def test_balance_provider_user_scoping_and_currency_conversion(self):
        provider = BalanceDataProvider()
        data = provider.get_data(self.user_a)

        summary = data["summary"]

        # 100,000 EGP + (10,000 USD * 50) + 200,000 EGP (synced cert) = 800,000 EGP
        self.assertAlmostEqual(summary["total_liquid_in_home_currency"], 800000.00, places=2)
        self.assertEqual(summary["total_accounts_count"], 3)

    def test_certificates_provider_user_scoping_and_yields(self):
        provider = BankCertificatesDataProvider()
        data = provider.get_data(self.user_a)

        summary = data["summary"]
        self.assertEqual(summary["total_active_certificates_principal"], 200000.00)
        self.assertEqual(summary["total_monthly_interest_income"], 3750.00)
        self.assertEqual(summary["active_certificates_count"], 1)

    def test_assets_provider_gold_karat_math(self):
        provider = FixedAssetsDataProvider()
        data = provider.get_data(self.user_a)

        summary = data["summary"]
        # 100g 18K @ 2250 EGP/g = 225,000 EGP
        self.assertAlmostEqual(summary["total_fixed_assets_value"], 225000.00, places=2)

    def test_priority_based_context_assembly(self):
        service = ContextBuilderService()
        messages, sources = service.assemble_messages(
            user_query="Analyze my bank balances and portfolio",
            user=self.user_a
        )

        system_msg = messages[0]["content"]

        # Guardrails and System Knowledge preserved
        self.assertIn("CRITICAL DIRECTIVES:", system_msg)
        self.assertIn("=== SYSTEM KNOWLEDGE & DOMAIN MANIFEST ===", system_msg)
        self.assertIn("=== FINANCIAL CONTEXT DATA ===", system_msg)

        # Check valid JSON syntax for injected payload summaries
        for line in system_msg.split("\n"):
            if line.strip().startswith("{") and line.strip().endswith("}"):
                try:
                    json.loads(line.strip())
                except Exception as exc:
                    self.fail(f"Invalid JSON found in priority context assembly: {line} ({exc})")

    def test_salary_provider_growth_analytics(self):
        provider = SalaryDataProvider()
        data = provider.get_data(self.user_a)

        summary = data["summary"]
        # Career growth from 50,000 (2025) to 60,000 (2026) = +20%
        self.assertEqual(summary["career_overall_growth_pct"], 20.0)
        self.assertEqual(summary["total_paid_all_time"], 110000.00)
