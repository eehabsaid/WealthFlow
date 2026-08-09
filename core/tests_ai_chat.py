import json
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AppSettings, AIConversation, AIMessage
from core.integrations.ai_provider import BaseAIProvider, OllamaProvider
from core.services.financial_advisor.registry import get_financial_advisor_payload, get_available_advisor_services
from core.services.ai.context_builder_service import ContextBuilderService

User = get_user_model()


class AIChatUnitTestSuite(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_user", password="password123")
        self.admin = User.objects.create_user(username="admin_user", password="password123", is_staff=True)

    def test_base_ai_provider_interface(self):
        # BaseAIProvider cannot be instantiated directly without abstract methods
        with self.assertRaises(TypeError):
            BaseAIProvider()

    @patch("urllib.request.urlopen")
    def test_ollama_provider_generate_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "model": "llama3.2:latest",
            "message": {"role": "assistant", "content": "Your net worth is 150,000 EGP."},
            "done": True,
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.2:latest", timeout=10)
        messages = [{"role": "user", "content": "What is my net worth?"}]
        res = provider.generate(messages)

        self.assertIsNone(res["error"])
        self.assertEqual(res["content"], "Your net worth is 150,000 EGP.")

    @patch("urllib.request.urlopen")
    def test_ollama_provider_generate_http_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://localhost:11434/api/chat",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=None,
        )

        provider = OllamaProvider(base_url="http://localhost:11434", timeout=5)
        res = provider.generate([{"role": "user", "content": "Hello"}])

        self.assertIsNotNone(res["error"])
        self.assertIn("HTTP 500", res["error"])
        self.assertEqual(res["content"], "")

    def test_advisor_service_registry(self):
        available = get_available_advisor_services()
        self.assertIn("overview", available)
        self.assertIn("cash_flow", available)
        self.assertIn("risk_analysis", available)
        self.assertIn("goal_planning", available)

        # Call payload via registry
        payload = get_financial_advisor_payload("overview")
        self.assertIsInstance(payload, dict)

        # Unknown service returns empty dict
        self.assertEqual(get_financial_advisor_payload("unknown_service"), {})

    def test_context_builder_service_budget_and_topic_relevance(self):
        AppSettings.set("ai_context_token_budget", "1500")
        builder = ContextBuilderService()

        self.assertEqual(builder.get_token_budget(), 1500)

        # Test topic relevance keyword matching
        services_portfolio = builder.determine_relevant_services("Tell me about my portfolio allocation")
        self.assertIn("portfolio_optimizer", services_portfolio)

        services_spending = builder.determine_relevant_services("What are my highest expense categories?")
        self.assertIn("spending_intelligence", services_spending)

        # Assemble messages
        messages, sources = builder.assemble_messages("What is my net worth?")
        self.assertGreater(len(messages), 0)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("CRITICAL DIRECTIVES", messages[0]["content"])
        self.assertIn("overview", sources)

    def test_ai_conversation_and_message_models_soft_delete(self):
        conv = AIConversation.objects.create(user=self.user, title="Financial Chat")
        self.assertFalse(conv.is_deleted)
        self.assertEqual(conv.title, "Financial Chat")

        AIMessage.objects.create(
            conversation=conv, role="user", content="Hello", sources=[]
        )
        AIMessage.objects.create(
            conversation=conv, role="assistant", content="Hi there!", sources=["overview"]
        )

        self.assertEqual(conv.messages.filter(is_deleted=False).count(), 2)
        conv_dict = conv.to_dict()
        self.assertEqual(conv_dict["messages_count"], 2)

        # Test soft delete
        conv.is_deleted = True
        conv.save()
        conv.messages.filter(is_deleted=False).update(is_deleted=True)

        self.assertTrue(AIConversation.objects.get(id=conv.id).is_deleted)
        self.assertEqual(AIMessage.objects.filter(conversation=conv, is_deleted=False).count(), 0)

    def test_ai_chat_view_unauthenticated(self):
        res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": "Hi"}), content_type="application/json")
        self.assertEqual(res.status_code, 401)

    def test_ai_chat_view_user_message_saved_when_disabled(self):
        self.client.force_login(self.user)
        AppSettings.set("ai_enabled", "false")

        res = self.client.post(
            "/api/financial-advisor/ai/chat/",
            json.dumps({"message": "What is my cash flow?"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["error_key"], "ai_chat_disabled_desc")
        self.assertIn("user_message", data)

        # Confirm user message was saved to database
        conv_id = data["conversation_id"]
        conv = AIConversation.objects.get(id=conv_id)
        user_msgs = conv.messages.filter(role="user")
        self.assertEqual(user_msgs.count(), 1)
        self.assertEqual(user_msgs.first().content, "What is my cash flow?")

    @patch.object(OllamaProvider, "generate")
    def test_ai_chat_view_success_flow(self, mock_generate):
        mock_generate.return_value = {
            "content": "Your projected monthly cash flow is positive 5,000 EGP.",
            "error": None,
        }

        self.client.force_login(self.user)
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_provider", "ollama")
        AppSettings.set("ai_history_window", "10")

        res = self.client.post(
            "/api/financial-advisor/ai/chat/",
            json.dumps({"message": "Predict my cash flow"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertIn("message", data)
        self.assertEqual(data["message"]["content"], "Your projected monthly cash flow is positive 5,000 EGP.")
        self.assertIn("sources", data)

    def test_ai_conversation_list_and_detail_views(self):
        self.client.force_login(self.user)
        conv = AIConversation.objects.create(user=self.user, title="Test Conversation")
        AIMessage.objects.create(conversation=conv, role="user", content="Test question")

        # GET list
        res_list = self.client.get("/api/financial-advisor/ai/conversations/")
        self.assertEqual(res_list.status_code, 200)
        convs = res_list.json()["conversations"]
        self.assertEqual(len(convs), 1)
        self.assertEqual(convs[0]["id"], conv.id)

        # GET detail
        res_detail = self.client.get(f"/api/financial-advisor/ai/conversations/{conv.id}/")
        self.assertEqual(res_detail.status_code, 200)
        detail_data = res_detail.json()["conversation"]
        self.assertEqual(len(detail_data["messages"]), 1)

        # DELETE soft-delete
        res_del = self.client.delete(f"/api/financial-advisor/ai/conversations/{conv.id}/")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.json()["ok"])

        # Confirm soft-deleted
        conv.refresh_from_db()
        self.assertTrue(conv.is_deleted)

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
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_provider", "ollama")

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
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_provider", "ollama")

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
        from core.services.ai.cache_manager import AICacheManager
        cache_mgr = AICacheManager()
        cache_mgr.invalidate(f"ai_loop_progress:{self.user.id}:{conv.id}")

        res_owned = self.client.get(f"/api/financial-advisor/ai/progress/?conversation_id={conv.id}")
        self.assertEqual(res_owned.status_code, 200)
        self.assertEqual(res_owned.json()["status"], "idle")
