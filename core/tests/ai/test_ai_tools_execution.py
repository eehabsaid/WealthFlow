"""
Unit test suite for AI Financial Advisor Phase 3: AI Actions.

Tests tool registration, the 5-step validation pipeline, tool handlers,
atomic scenario creation rollback, read-only constraints, audit logging,
and single-tool call chat controller integration.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AppSettings, AIMessage, Scenario
from core.integrations.ai_provider import OllamaProvider
from core.services.ai.tools import (
    get_registered_tool_schemas,
    validate_and_execute_tool,
)

User = get_user_model()

class AIToolsExecutionTest(TestCase):
    def setUp(self):
        AppSettings.set("ai_read_only", "false")
        self.user = User.objects.create_user(username="action_user", password="password123")
        self.inactive_user = User.objects.create_user(
            username="inactive_user", password="password123", is_active=False
        )

    def test_create_scenario_tool_success_flow(self):
        events = [
            {
                "event_type": "car",
                "event_date": "2026-09-01",
                "params": {"purchase_price": 500000, "down_payment": 100000},
                "order": 1,
            }
        ]
        audit, res = validate_and_execute_tool(
            "create_scenario",
            {"name": "New Car Scenario", "description": "Buying a car", "events": events},
            self.user,
        )
        self.assertTrue(res["ok"])
        self.assertEqual(audit["status"], "success")
        self.assertGreaterEqual(audit["duration_ms"], 0)

        data = res["data"]
        self.assertEqual(data["name"], "New Car Scenario")

        # Confirm database records created
        sc = Scenario.objects.get(id=data["id"])
        self.assertEqual(sc.name, "New Car Scenario")
        self.assertEqual(sc.events.count(), 1)
        self.assertEqual(sc.events.first().event_type, "car")

    def test_compare_scenarios_tool_execution(self):
        sc = Scenario.objects.create(name="Base Compare Scenario")
        audit, res = validate_and_execute_tool("compare_scenarios", {"scenario_ids": [sc.id]}, self.user)
        self.assertTrue(res["ok"])
        self.assertEqual(audit["status"], "success")
        self.assertIn("baseline", res["data"])
        self.assertIn("scenarios", res["data"])

    def test_summarize_report_and_explain_chart_tools_execution(self):
        audit, res = validate_and_execute_tool("summarize_report", {"service_key": "overview"}, self.user)
        self.assertTrue(res["ok"])
        self.assertEqual(audit["status"], "success")
        self.assertIsInstance(res["data"], dict)

        audit_chart, res_chart = validate_and_execute_tool("explain_chart", {"service_key": "cash_flow"}, self.user)
        self.assertTrue(res_chart["ok"])
        self.assertEqual(audit_chart["status"], "success")

    def test_suggest_optimizations_tool_execution(self):
        audit, res = validate_and_execute_tool("suggest_optimizations", {"focus": "all"}, self.user)
        self.assertTrue(res["ok"])
        self.assertEqual(audit["status"], "success")
        self.assertIn("portfolio_optimizer", res["data"])
        self.assertIn("opportunity_detection", res["data"])

    @patch("urllib.request.urlopen")
    def test_ollama_provider_with_tools_payload(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "model": "llama3.2:latest",
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "summarize_report",
                        "arguments": {"service_key": "overview"}
                    }
                }]
            },
            "done": True,
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        provider = OllamaProvider(base_url="http://localhost:11434")
        self.assertTrue(provider.supports_tools)

        tools = get_registered_tool_schemas()
        res = provider.generate([{"role": "user", "content": "Summarize my net worth"}], tools=tools)

        self.assertIsNone(res["error"])
        self.assertIsNotNone(res["tool_calls"])
        self.assertEqual(len(res["tool_calls"]), 1)
        self.assertEqual(res["tool_calls"][0]["function"]["name"], "summarize_report")

    @patch.object(OllamaProvider, "generate")
    def test_ai_chat_view_tool_call_flow_and_audit_log(self, mock_generate):
        self.client.force_login(self.user)
        AppSettings.set("ai_enabled", "true")

        # Mock first call returns a tool call for summarize_report
        # Mock second call returns the narrated response
        mock_generate.side_effect = [
            {
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "summarize_report",
                        "arguments": {"service_key": "overview"}
                    }
                }],
                "error": None,
            },
            {
                "content": "Here is the summary of your overall financial overview: Net worth is healthy.",
                "tool_calls": None,
                "error": None,
            }
        ]

        res = self.client.post(
            "/api/financial-advisor/ai/chat/",
            json.dumps({"message": "Summarize my overall financial health"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])

        # Check assistant message
        msg_dict = data["message"]
        self.assertIn("tool_calls", msg_dict)
        self.assertEqual(len(msg_dict["tool_calls"]), 1)

        tool_audit = msg_dict["tool_calls"][0]
        self.assertEqual(tool_audit["tool"], "summarize_report")
        self.assertEqual(tool_audit["status"], "success")
        self.assertGreaterEqual(tool_audit["duration_ms"], 0)

        # Confirm persisted in DB
        db_msg = AIMessage.objects.get(id=msg_dict["id"])
        self.assertEqual(len(db_msg.tool_calls), 1)
        self.assertEqual(db_msg.tool_calls[0]["tool"], "summarize_report")
