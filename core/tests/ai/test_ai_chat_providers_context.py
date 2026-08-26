import json
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AppSettings, AIConversation, AIMessage
from core.integrations.ai_provider import BaseAIProvider, OllamaProvider
from core.services.financial_advisor.registry import get_financial_advisor_payload, get_available_advisor_services
from core.services.ai.context_builder_service import ContextBuilderService

User = get_user_model()

class AIChatProvidersContextTest(TestCase):
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
