"""AI chat view tests: investigation loop, repeat prevention and progress view."""


import json
from unittest.mock import patch

from ai.models import AISetting
from ai.models.ai_conversation import AIConversation
from ai.integrations.ai_provider import OllamaProvider
from .ai_chat_views_support import AIChatViewsBase


class AIChatViewsInvestigationLoopTest(AIChatViewsBase):
    @patch.object(OllamaProvider, "generate")
    def test_multi_step_investigation_loop(self, mock_generate):
        """Verify model can chain multiple tool calls in sequence up to MAX_TOOL_ITERATIONS."""
        # 1st call: returns tool_call query_application_data
        # 2nd call: returns tool_call summarize_report
        # 3rd call: returns final text answer
        mock_generate.side_effect = [
            {
                "content": "",
                "error": None,
                "tool_calls": [{"name": "query_application_data", "arguments": {"query_type": "net_worth"}}],
            },
            {
                "content": "",
                "error": None,
                "tool_calls": [{"name": "summarize_report", "arguments": {"service_key": "overview"}}],
            },
            {
                "content": "Based on my 2-step analysis, your net worth and overview are solid.",
                "error": None,
                "tool_calls": [],
            },
        ]

        self.client.force_login(self.user)
        AISetting.set("ai_enabled", "true")
        AISetting.set("ai_provider", "ollama")

        res = self.client.post(
            "/api/financial-advisor/ai/chat/",
            json.dumps({"message": "Analyze my financial situation"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["message"]["content"], "Based on my 2-step analysis, your net worth and overview are solid.")
        tool_calls = data["message"]["tool_calls"]
        self.assertEqual(len(tool_calls), 2)
        self.assertEqual(tool_calls[0]["tool"], "query_application_data")
        self.assertEqual(tool_calls[0]["step"], 1)
        self.assertEqual(tool_calls[1]["tool"], "summarize_report")
        self.assertEqual(tool_calls[1]["step"], 2)

    @patch.object(OllamaProvider, "generate")
    def test_repeat_tool_call_prevention(self, mock_generate):
        """Verify identical (tool, arguments) requests are blocked from executing twice."""
        mock_generate.side_effect = [
            {
                "content": "",
                "error": None,
                "tool_calls": [{"name": "query_application_data", "arguments": {"query_type": "net_worth"}}],
            },
            {
                "content": "",
                "error": None,
                "tool_calls": [{"name": "query_application_data", "arguments": {"query_type": "net_worth"}}],
            },
            {
                "content": "Duplicate was blocked gracefully.",
                "error": None,
                "tool_calls": [],
            },
        ]

        self.client.force_login(self.user)
        AISetting.set("ai_enabled", "true")
        AISetting.set("ai_provider", "ollama")

        res = self.client.post(
            "/api/financial-advisor/ai/chat/",
            json.dumps({"message": "Check net worth twice"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        tool_calls = data["message"]["tool_calls"]
        # Should only execute tool ONCE because second attempt was identical fingerprint
        self.assertEqual(len(tool_calls), 1)

    def test_progress_view_auth_and_ownership(self):
        """Verify progress endpoint auth, invalid conversation ownership, and status response."""
        # Unauthenticated request
        res_unauth = self.client.get("/api/financial-advisor/ai/progress/?conversation_id=1")
        self.assertEqual(res_unauth.status_code, 401)

        self.client.force_login(self.user)

        # Invalid conversation ID / not owned by user
        res_other = self.client.get("/api/financial-advisor/ai/progress/?conversation_id=999999")
        self.assertEqual(res_other.status_code, 200)
        self.assertEqual(res_other.json()["status"], "idle")

        # Owned conversation with no active cache
        conv = AIConversation.objects.create(user=self.user, title="Owned Conv")
        # Ensure progress key for this specific conversation is clear
        from ai.services.cache_manager import AICacheManager
        cache_mgr = AICacheManager()
        cache_mgr.invalidate(f"ai_loop_progress:{self.user.id}:{conv.id}")

        res_owned = self.client.get(f"/api/financial-advisor/ai/progress/?conversation_id={conv.id}")
        self.assertEqual(res_owned.status_code, 200)
        self.assertEqual(res_owned.json()["status"], "idle")
