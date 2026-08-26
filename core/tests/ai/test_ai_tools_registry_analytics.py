"""
Unit test suite for new AI read-only tools, question domain selection, and read-only configuration.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.services.ai.tools import (
    validate_and_execute_tool,
)

User = get_user_model()

class NewAIToolsRegistryAnalyticsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_ai_user", password="Password123!")

    def test_tool_registry_and_validation(self):
        from core.services.ai.tools_registry import validate_tool_registry
        errs = validate_tool_registry()
        self.assertEqual(len(errs), 0)

    def test_ai_context_orchestrator(self):
        from core.services.ai.orchestrator import AIContextOrchestrator
        res = AIContextOrchestrator.assemble_context("business_analysis", self.user, {"limit": 5})
        self.assertIn("business_data", res)
        self.assertIn("capability_registry", res)
        self.assertIn("_explanation_metadata", res)

        meta = res["_explanation_metadata"]
        self.assertEqual(meta["intent"], "business_analysis")
        self.assertIn("business_data_providers", meta["context_sources"])
        self.assertIn(meta["confidence"], ("high", "medium", "low"))

    def test_i18n_translation_files_no_duplicate_keys(self):
        import os
        import re
        lang_files = ["static/i18n/en.json", "static/i18n/ar.json", "static/i18n/fr.json", "static/i18n/de.json"]
        for filepath in lang_files:
            self.assertTrue(os.path.exists(filepath), f"File missing: {filepath}")
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            raw_keys = re.findall(r'"([^"\\]+(?:\\.[^"\\]*)*)"\s*:', content)
            seen = set()
            duplicates = []
            for k in raw_keys:
                if k in seen:
                    duplicates.append(k)
                seen.add(k)
            self.assertEqual(len(duplicates), 0, f"Duplicate keys found in {filepath}: {duplicates}")

    def test_query_application_data_intent_driven_matching(self):
        from core.services.ai.providers import get_relevant_providers_data

        # 1. Portfolio query matching liquid deposits, certificates, gold, and real estate assets
        portfolio_res = get_relevant_providers_data(
            self.user,
            search_query="Analyze my current portfolio breakdown across liquid bank deposits, certificates, gold, and real estate assets"
        )
        meta_portfolio = portfolio_res.get("_explanation_metadata", {})
        self.assertTrue(meta_portfolio.get("intent_matched"))
        matched_portfolio = meta_portfolio.get("matched_providers", [])

        self.assertIn("balance", matched_portfolio)
        self.assertIn("bank_certificates", matched_portfolio)
        self.assertIn("fixed_assets", matched_portfolio)
        self.assertNotIn("salary", matched_portfolio)
        self.assertNotIn("expenses", matched_portfolio)

        # 2. Salary query matching salary provider and excluding fixed assets and certificates
        salary_res = get_relevant_providers_data(
            self.user,
            search_query="What is my monthly salary income and employment details?"
        )
        meta_salary = salary_res.get("_explanation_metadata", {})
        self.assertTrue(meta_salary.get("intent_matched"))
        matched_salary = meta_salary.get("matched_providers", [])

        self.assertIn("salary", matched_salary)
        self.assertNotIn("bank_certificates", matched_salary)
        # 3. Tool execution test with search_query parameter
        audit_rec, tool_res = validate_and_execute_tool(
            "query_application_data",
            {"search_query": "bank certificates and maturity"},
            self.user
        )
        self.assertEqual(audit_rec["status"], "success")
        self.assertIn("bank_certificates", tool_res["data"])
        self.assertNotIn("salary", tool_res["data"])

    def test_salary_data_provider_complete_analytics_and_currency(self):
        from core.models import Company, SalaryEntry
        from core.services.ai.providers.salary_provider import SalaryDataProvider

        company = Company.objects.create(name="Test Giza Systems", is_active=True)
        SalaryEntry.objects.create(company=company, year=2026, month="January", paid=87643.86, expected=87643.86, bonus=0)
        SalaryEntry.objects.create(company=company, year=2026, month="February", paid=87643.86, expected=87643.86, bonus=0)
        SalaryEntry.objects.create(company=company, year=2026, month="March", paid=87643.86, expected=87643.86, bonus=0)
        SalaryEntry.objects.create(company=company, year=2026, month="April", paid=89030.96, expected=89030.96, bonus=0)
        SalaryEntry.objects.create(company=company, year=2026, month="May", paid=89030.96, expected=89030.96, bonus=0)
        SalaryEntry.objects.create(company=company, year=2026, month="June", paid=89030.96, expected=89030.96, bonus=0)
        SalaryEntry.objects.create(company=company, year=2026, month="July", paid=89030.00, expected=89030.00, bonus=0)

        provider = SalaryDataProvider()
        data = provider.get_data(self.user)

        self.assertEqual(data["currency"], "EGP")
        self.assertIn("summary", data)
        self.assertIn("latest_active_year", data)
        self.assertEqual(data["latest_active_year"], 2026)
        self.assertIn("recent_monthly_timeline", data)

        summary = data["summary"]
        self.assertIn("total_paid_all_time_formatted", summary)
        self.assertIn("EGP", summary["total_paid_all_time_formatted"])
        self.assertEqual(summary["currency"], "EGP")

        latest_summary = data["latest_active_year_summary"]
        self.assertEqual(latest_summary["year"], 2026)
        self.assertAlmostEqual(latest_summary["total_paid"], 619054.46, places=2)
        self.assertEqual(latest_summary["total_paid_formatted"], "619,054.46 EGP")
        self.assertEqual(latest_summary["entries_count"], 7)

        timeline = data["recent_monthly_timeline"]
        months_found = [m["month"] for m in timeline if m["year"] == 2026]
        self.assertIn("February", months_found)
        self.assertIn("April", months_found)
        for entry in timeline:
            self.assertEqual(entry["currency"], "EGP")
            self.assertIn("EGP", entry["paid_formatted"])
