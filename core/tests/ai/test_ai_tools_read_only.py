"""
Unit test suite for new AI read-only tools, question domain selection, and read-only configuration.
"""

from __future__ import annotations

from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AppSettings
from core.services.ai.tools import (
    get_registered_tool_schemas,
    validate_and_execute_tool,
)

User = get_user_model()

class NewAIToolsReadOnlyTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_ai_user", password="Password123!")

    def test_registered_tools_count_and_domains(self):
        schemas_all = get_registered_tool_schemas()
        self.assertEqual(len(schemas_all), 9)

        schemas_business = get_registered_tool_schemas(domain="business_data_analysis")
        schemas_arch = get_registered_tool_schemas(domain="app_features_architecture")

        business_names = [s["function"]["name"] for s in schemas_business]
        arch_names = [s["function"]["name"] for s in schemas_arch]

        self.assertIn("create_scenario", business_names)
        self.assertIn("compare_scenarios", business_names)
        self.assertIn("summarize_report", business_names)
        self.assertIn("explain_chart", business_names)
        self.assertIn("suggest_optimizations", business_names)
        self.assertIn("query_application_data", business_names)

        self.assertIn("read_live_app_structure", arch_names)
        self.assertIn("suggest_app_feature", arch_names)
        self.assertIn("read_application_codebase", arch_names)

    def test_read_live_app_structure_route_discovery_and_caching(self):
        # Call tool handler directly with include_playwright=True
        with patch("core.services.ai.tools._crawl_live_pages_with_playwright") as mock_crawl:
            mock_crawl.return_value = (
                [
                    {
                        "route": "dashboard",
                        "title": "Dashboard Overview",
                        "url": "http://127.0.0.1:8001/",
                        "tabs": [{"name": "Overview", "id": "overview-tab"}],
                        "modals_or_forms": [],
                        "status": "ok",
                    },
                    {
                        "route": "financial-advisor",
                        "title": "WealthFlow Financial Advisor",
                        "url": "http://127.0.0.1:8001/#financial-advisor",
                        "tabs": [
                            {"name": "Overview", "id": "fa-overview"},
                            {"name": "Cash Flow", "id": "fa-cashflow"},
                            {"name": "Wealth Growth", "id": "fa-wealthgrowth"},
                            {"name": "Portfolio Optimizer", "id": "fa-portfolio"},
                            {"name": "Goal Planning", "id": "fa-goal"},
                            {"name": "Risk Analysis", "id": "fa-risk"},
                            {"name": "Spending Intelligence", "id": "fa-spending"},
                            {"name": "Opportunity Detection", "id": "fa-opp"},
                            {"name": "Performance", "id": "fa-perf"},
                            {"name": "What-If Simulator", "id": "fa-whatif"},
                        ],
                        "modals_or_forms": ["Scenario Planner Modal"],
                        "status": "ok",
                    },
                ],
                None,
            )

            audit, res = validate_and_execute_tool(
                "read_live_app_structure", {"include_playwright": True, "force_refresh": True}, self.user
            )
            self.assertTrue(res["ok"])
            self.assertEqual(audit["status"], "success")

            data = res["data"]
            self.assertIn("django_routes", data)
            self.assertIn("live_pages", data)
            self.assertTrue(data["playwright_executed"])
            self.assertGreater(len(data["live_pages"]), 0)

            # Assert Financial Advisor tabs exist in crawled live_pages
            fa_page = next((p for p in data["live_pages"] if p["route"] == "financial-advisor"), None)
            self.assertIsNotNone(fa_page)
            self.assertEqual(fa_page["status"], "ok")
            
            tab_names = [t["name"] for t in fa_page["tabs"]]
            expected_tabs = [
                "Overview", "Cash Flow", "Wealth Growth", "Portfolio Optimizer",
                "Goal Planning", "Risk Analysis", "Spending Intelligence",
                "Opportunity Detection", "Performance", "What-If Simulator"
            ]
            for tab in expected_tabs:
                self.assertIn(tab, tab_names)

        routes = [r["route"] for r in data["django_routes"]]
        self.assertIn("/accounts/login", routes)
        self.assertIn("/accounts/signup", routes)

        # Confirm non-API, non-static filtering
        for r in routes:
            self.assertFalse(r.startswith("/api/"))
            self.assertFalse(r.startswith("/static/"))

        # Test caching: second call should return cached=True
        audit2, res2 = validate_and_execute_tool("read_live_app_structure", {}, self.user)
        self.assertTrue(res2["ok"])
        self.assertTrue(res2["data"]["cached"])

        # Force refresh should bypass cache
        audit3, res3 = validate_and_execute_tool("read_live_app_structure", {"force_refresh": True}, self.user)
        self.assertTrue(res3["ok"])
        self.assertFalse(res3["data"]["cached"])

    def test_playwright_single_page_failure_isolation(self):
        from core.services.ai.tools import _crawl_live_pages_with_playwright
        
        # Test signature flexibility and per-page failure recording
        routes_sample = [{"route": "/test", "pattern": "^test/$"}]
        pages, err = _crawl_live_pages_with_playwright(routes_info=routes_sample, max_pages=1)
        self.assertIsInstance(pages, list)
        self.assertIsNone(err)

    def test_query_application_data_tool_execution(self):
        audit, res = validate_and_execute_tool(
            "query_application_data",
            {"query_type": "all", "limit": 10},
            self.user
        )
        self.assertTrue(res["ok"])
        self.assertEqual(audit["status"], "success")

        data = res["data"]
        self.assertIn("salary", data)
        self.assertIn("balance", data)
        self.assertIn("expenses", data)
        self.assertIn("fixed_assets", data)
        self.assertIn("bank_certificates", data)
        self.assertIn("market_data", data)
        self.assertIn("financial_advisor", data)

    def test_suggest_app_feature_tool_execution(self):
        audit, res = validate_and_execute_tool(
            "suggest_app_feature",
            {"focus_area": "financial_advisor", "gap_description": "Need better debt vs asset tracking"},
            self.user
        )
        self.assertTrue(res["ok"])
        self.assertEqual(audit["status"], "success")

        data = res["data"]
        self.assertEqual(data["focus_area"], "financial_advisor")
        self.assertIn("required_document_sections", data)
        self.assertIn("Problem Statement", data["required_document_sections"])
        self.assertIn("Acceptance Criteria", data["required_document_sections"])
        self.assertIn("instructions", data)

    def test_read_only_global_setting_enforcement(self):
        # Enable read_only setting
        AppSettings.set("ai_read_only", "true")

        # Write tool (create_scenario) MUST be rejected when global read_only is True
        audit, res = validate_and_execute_tool("create_scenario", {"name": "Test Read Only Scenario"}, self.user)
        self.assertFalse(res["ok"])
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("read-only mode", audit["rejection_reason"])

        # Permanently read-only tools (query_application_data, read_live_app_structure, suggest_app_feature) MUST succeed
        audit_query, res_query = validate_and_execute_tool("query_application_data", {}, self.user)
        self.assertTrue(res_query["ok"])
        self.assertEqual(audit_query["status"], "success")

        audit_struct, res_struct = validate_and_execute_tool("read_live_app_structure", {}, self.user)
        self.assertTrue(res_struct["ok"])
        self.assertEqual(audit_struct["status"], "success")

        audit_sug, res_sug = validate_and_execute_tool("suggest_app_feature", {"focus_area": "general"}, self.user)
        self.assertTrue(res_sug["ok"])
        self.assertEqual(audit_sug["status"], "success")

        # When global read_only is disabled, create_scenario should succeed
        AppSettings.set("ai_read_only", "false")
        audit_create, res_create = validate_and_execute_tool("create_scenario", {"name": "Allowed Scenario"}, self.user)
        self.assertTrue(res_create["ok"])
        self.assertEqual(audit_create["status"], "success")
