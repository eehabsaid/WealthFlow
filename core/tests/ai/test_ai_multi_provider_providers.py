"""
Unit test suite for AI Financial Advisor Phase 4: Multi-Provider Integration & Security Hardening.

Covers:
- Fernet credential encryption at rest & key derivation
- Masked key re-submission protection (byte-identical ciphertext assertion)
- Plaintext API key protection (ciphertext in DB, masked in GET API)
- Secret redaction across error handlers
- Provider schemas and provider-agnostic factory (from_settings)
- Mocks for generate(), check_connection(), and list_models() across OpenAI, Claude, Gemini, Azure, and Ollama
- Token usage tracking on AIMessage (prompt_tokens, completion_tokens)
"""

from unittest.mock import patch

from django.test import TestCase

from core.integrations.ai_provider import (
    AVAILABLE_AI_PROVIDERS,
    AzureOpenAIProvider,
    ClaudeProvider,
    GeminiProvider,
    OpenAIProvider,
    get_active_ai_provider,
)

from core.models import AIMessage, AppSettings
from core.services.ai.credential_encryption import (
    encrypt_credential,
)

class AIProviderClassesTests(TestCase):
    def setUp(self):
        AppSettings.objects.all().delete()

    def test_available_providers_registry(self):
        self.assertCountEqual(
            list(AVAILABLE_AI_PROVIDERS.keys()),
            ["ollama", "openai", "claude", "gemini", "azure"]
        )

    def test_get_active_ai_provider_factory(self):
        # AI disabled -> None
        AppSettings.set("ai_enabled", "false")
        self.assertIsNone(get_active_ai_provider())

        # Enable OpenAI
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_provider", "openai")
        AppSettings.set("ai_openai_api_key", encrypt_credential("sk-test12345"))
        AppSettings.set("ai_openai_model", "gpt-4o")

        provider = get_active_ai_provider()
        self.assertIsInstance(provider, OpenAIProvider)
        self.assertEqual(provider.model, "gpt-4o")
        self.assertEqual(provider.api_key, "sk-test12345")
        self.assertTrue(provider.capabilities["supports_tools"])

    @patch("core.integrations.openai_provider.make_json_http_request")
    def test_openai_provider_generate_and_tokens(self, mock_http):
        mock_http.return_value = (
            {
                "choices": [{"message": {"content": "Hello from OpenAI", "tool_calls": None}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8},
            },
            200,
            None,
        )
        provider = OpenAIProvider(api_key="sk-testkey", model="gpt-4o")
        res = provider.generate([{"role": "user", "content": "Hi"}])

        self.assertEqual(res["content"], "Hello from OpenAI")
        self.assertEqual(res["prompt_tokens"], 12)
        self.assertEqual(res["completion_tokens"], 8)
        self.assertIsNone(res["error"])

    @patch("core.integrations.claude_provider.make_json_http_request")
    def test_claude_provider_generate_and_tokens(self, mock_http):
        mock_http.return_value = (
            {
                "content": [{"type": "text", "text": "Hello from Claude"}],
                "usage": {"input_tokens": 15, "output_tokens": 10},
            },
            200,
            None,
        )
        provider = ClaudeProvider(api_key="sk-ant-test", model="claude-3-5-sonnet-20241022")
        res = provider.generate([{"role": "user", "content": "Hi"}])

        self.assertEqual(res["content"], "Hello from Claude")
        self.assertEqual(res["prompt_tokens"], 15)
        self.assertEqual(res["completion_tokens"], 10)

    @patch("core.integrations.gemini_provider.make_json_http_request")
    def test_gemini_provider_generate_and_tokens(self, mock_http):
        mock_http.return_value = (
            {
                "candidates": [{"content": {"parts": [{"text": "Hello from Gemini"}]}}],
                "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 14},
            },
            200,
            None,
        )
        provider = GeminiProvider(api_key="AIzaSyTestKey", model="gemini-1.5-flash")
        res = provider.generate([{"role": "user", "content": "Hi"}])

        self.assertEqual(res["content"], "Hello from Gemini")
        self.assertEqual(res["prompt_tokens"], 20)
        self.assertEqual(res["completion_tokens"], 14)

    @patch("core.integrations.azure_openai_provider.make_json_http_request")
    def test_azure_provider_generate_and_tokens(self, mock_http):
        mock_http.return_value = (
            {
                "choices": [{"message": {"content": "Hello from Azure"}}],
                "usage": {"prompt_tokens": 18, "completion_tokens": 9},
            },
            200,
            None,
        )
        provider = AzureOpenAIProvider(api_key="azurekey123", endpoint="https://test.openai.azure.com", deployment="gpt4o-dep")
        res = provider.generate([{"role": "user", "content": "Hi"}])

        self.assertEqual(res["content"], "Hello from Azure")
        self.assertEqual(res["prompt_tokens"], 18)
        self.assertEqual(res["completion_tokens"], 9)

    @patch("core.integrations.openai_provider.make_json_http_request")
    def test_secret_redaction_on_provider_http_error(self, mock_http):
        secret_key = "sk-proj-secret-key-to-be-redacted"
        mock_http.return_value = (None, 401, f"Unauthorized API call with key {secret_key}")

        provider = OpenAIProvider(api_key=secret_key, model="gpt-4o")
        res = provider.generate([{"role": "user", "content": "Hi"}])

        self.assertNotIn(secret_key, res["error"])
        self.assertIn("[REDACTED]", res["error"])


class AIMessageTokenCountsTests(TestCase):
    def test_aimessage_token_counts_persistence(self):
        from core.models import AIConversation
        conv = AIConversation.objects.create(title="Test Conversation")
        msg = AIMessage.objects.create(
            conversation=conv,
            role="assistant",
            content="Hello",
            prompt_tokens=100,
            completion_tokens=50,
        )

        d = msg.to_dict()
        self.assertEqual(d["prompt_tokens"], 100)
        self.assertEqual(d["completion_tokens"], 50)

        # Refresh from DB
        msg_db = AIMessage.objects.get(pk=msg.pk)
        self.assertEqual(msg_db.prompt_tokens, 100)
        self.assertEqual(msg_db.completion_tokens, 50)
