"""
Unit test suite for new AI read-only tools, question domain selection, and read-only configuration.
"""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AppSettings
from core.services.ai.tools import (
    get_registered_tool_schemas,
    validate_and_execute_tool,
)

User = get_user_model()


class NewAIToolsUnitTestSuite(TestCase):
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
        self.assertIn("balances", data)
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

    def test_ai_chat_view_question_domain_filtering(self):
        self.client.force_login(self.user)
        AppSettings.set("ai_enabled", "true")

        with patch("core.views.ai_chat_views.get_active_ai_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.supports_tools = True
            mock_provider.generate.return_value = {
                "content": "Selected domain response",
                "tool_calls": None,
                "error": None,
            }
            mock_get_provider.return_value = mock_provider

            res = self.client.post(
                "/api/financial-advisor/ai/chat/",
                json.dumps({
                    "message": "What pages exist?",
                    "question_domain": "app_features_architecture",
                }),
                content_type="application/json",
            )
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json()["ok"])

            # Verify generate was called with tools param filtered by domain
            tools_passed = mock_provider.generate.call_args[1].get("tools") or []
            tool_names = [t["function"]["name"] for t in tools_passed]
            self.assertIn("read_live_app_structure", tool_names)
            self.assertNotIn("create_scenario", tool_names)

    def test_ai_settings_read_only_endpoint(self):
        self.client.force_login(self.user)
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        # GET settings returns ai_read_only
        res_get = self.client.get("/api/settings/ai/")
        self.assertEqual(res_get.status_code, 200)
        self.assertIn("ai_read_only", res_get.json())

        # POST settings saves ai_read_only
        res_post = self.client.post(
            "/api/settings/ai/",
            json.dumps({"ai_read_only": False, "ai_provider": "ollama"}),
            content_type="application/json",
        )
        self.assertEqual(res_post.status_code, 200)
        self.assertEqual(AppSettings.get("ai_read_only"), "false")

    def test_read_application_codebase_execution(self):
        audit, res = validate_and_execute_tool(
            "read_application_codebase",
            {"search_term": "Expense", "module_type": "service"},
            self.user,
        )
        self.assertTrue(res["ok"])
        self.assertEqual(audit["status"], "success")

        data = res["data"]
        self.assertIn("total_indexed_classes", data)
        self.assertIn("architecture_index", data)
        self.assertGreaterEqual(data["total_indexed_classes"], 1)

    def test_data_provider_registry(self):
        from core.services.ai.providers import DATA_PROVIDER_REGISTRY, get_all_providers_data
        self.assertIn("salary", DATA_PROVIDER_REGISTRY)
        self.assertIn("expenses", DATA_PROVIDER_REGISTRY)

        data = get_all_providers_data(self.user)
        self.assertIn("salary", data)
        self.assertIn("bank_certificates", data)
        self.assertIn("market_data", data)
        self.assertIn("balances", data)
        self.assertIn("fixed_assets", data)

    def test_ai_cache_manager(self):
        from core.services.ai.cache_manager import AICacheManager
        cache = AICacheManager()
        cache.set("test_key_123", {"foo": "bar"}, ttl_seconds=100.0)
        val = cache.get("test_key_123")
        self.assertEqual(val, {"foo": "bar"})
        cache.invalidate("test_key_123")
        self.assertIsNone(cache.get("test_key_123"))

    def test_capability_registry(self):
        from core.services.ai.capability_registry import CapabilityRegistry
        res = CapabilityRegistry.get_capabilities(search_term="Expense")
        self.assertIn("total_capabilities_registered", res)
        self.assertGreaterEqual(res["total_capabilities_registered"], 1)

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

        self.assertIn("balances", matched_portfolio)
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
        self.assertNotIn("fixed_assets", matched_salary)

        # 3. Tool execution test with search_query parameter
        audit_rec, tool_res = validate_and_execute_tool(
            "query_application_data",
            {"search_query": "bank certificates and maturity"},
            self.user
        )
        self.assertTrue(audit_rec["success"])
        self.assertIn("bank_certificates", tool_res)
        self.assertNotIn("salary", tool_res)

