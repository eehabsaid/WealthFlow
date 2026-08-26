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
    validate_and_execute_tool,
)

User = get_user_model()

class NewAIToolsDomainTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_ai_user", password="Password123!")

    def test_ai_chat_view_question_domain_filtering(self):
        self.client.force_login(self.user)
        AppSettings.set("ai_enabled", "true")

        with patch("core.views.ai_chat.ai_chat_core_views.get_active_ai_provider") as mock_get_provider:
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
        self.assertIn("balance", data)
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
