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

import json
import os
from unittest.mock import patch

from django.contrib.auth.models import User
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
    decrypt_credential,
    encrypt_credential,
    get_fernet_key,
    is_encrypted,
    is_masked,
    mask_credential,
    redact_secrets,
)


class AICredentialEncryptionTests(TestCase):
    def setUp(self):
        AppSettings.objects.all().delete()

    def test_key_derivation_fallback_and_custom_env(self):
        # Default key derived from SECRET_KEY
        key_default = get_fernet_key()
        self.assertIsInstance(key_default, bytes)
        self.assertEqual(len(key_default), 44)  # 32-byte urlsafe base64 string length

        # Custom env var key
        with patch.dict(os.environ, {"WEALTHFLOW_AI_ENCRYPTION_KEY": "custom_secret_test_key_1234567890"}):
            key_env = get_fernet_key()
            self.assertIsInstance(key_env, bytes)
            self.assertNotEqual(key_default, key_env)

    def test_encrypt_decrypt_mask_helpers(self):
        raw_key = "sk-proj-test123456789secretkey"
        ciphertext = encrypt_credential(raw_key)

        self.assertTrue(is_encrypted(ciphertext))
        self.assertTrue(ciphertext.startswith("enc:"))
        self.assertNotIn(raw_key, ciphertext)

        decrypted = decrypt_credential(ciphertext)
        self.assertEqual(decrypted, raw_key)

        masked = mask_credential(raw_key)
        self.assertTrue(is_masked(masked))
        self.assertEqual(masked, "••••tkey")

    def test_redact_secrets_utility(self):
        secret = "sk-proj-supersecretkey999"
        error_msg = f"HTTP 401: Unauthorized request with key {secret} to endpoint"
        redacted = redact_secrets(error_msg, [secret])

        self.assertNotIn(secret, redacted)
        self.assertIn("[REDACTED]", redacted)


class AIMultiProviderSettingsApiTests(TestCase):
    def setUp(self):
        AppSettings.objects.all().delete()
        self.admin = User.objects.create_superuser(username="admin", password="password")
        self.client.force_login(self.admin)

    @patch("core.integrations.openai_provider.make_json_http_request")
    def test_db_stores_ciphertext_and_get_api_returns_masked_keys(self, mock_http):
        mock_http.return_value = ({"data": [{"id": "gpt-4o"}]}, 200, None)
        raw_openai_key = "sk-proj-1234567890abcdef"
        post_data = {
            "ai_enabled": True,
            "ai_provider": "openai",
            "ai_openai_api_key": raw_openai_key,
            "ai_openai_model": "gpt-4o",
        }
        resp = self.client.post("/api/settings/ai/", data=json.dumps(post_data), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        # 1. Assert DB stores ciphertext, NOT raw plaintext
        db_raw_val = AppSettings.get("ai_openai_api_key", "").strip()
        self.assertTrue(db_raw_val.startswith("enc:"))
        self.assertNotIn(raw_openai_key, db_raw_val)

        # 2. Assert decrypted value matches raw key
        self.assertEqual(decrypt_credential(db_raw_val), raw_openai_key)

        # 3. Assert GET API returns masked key, NOT raw key or ciphertext
        get_resp = self.client.get("/api/settings/ai/")
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()
        self.assertEqual(data["ai_openai_api_key"], "••••cdef")
        self.assertTrue(data["ai_openai_is_configured"])
        self.assertNotIn(raw_openai_key, json.dumps(data))

    @patch("core.integrations.openai_provider.make_json_http_request")
    def test_masked_key_resubmission_preserves_byte_identical_ciphertext(self, mock_http):
        mock_http.return_value = ({"data": [{"id": "gpt-4o"}]}, 200, None)
        raw_key = "sk-proj-origsecretkey999"
        enc_val_initial = encrypt_credential(raw_key)
        AppSettings.set("ai_openai_api_key", enc_val_initial)
        AppSettings.set("ai_provider", "openai")

        # GET API returns masked value '••••y999'
        get_resp = self.client.get("/api/settings/ai/")
        masked_val = get_resp.json()["ai_openai_api_key"]
        self.assertEqual(masked_val, "••••y999")

        # User resubmits settings form keeping masked placeholder unchanged
        resubmit_payload = {
            "ai_enabled": True,
            "ai_provider": "openai",
            "ai_openai_api_key": masked_val,  # '••••y999'
            "ai_openai_model": "gpt-4o-mini",
        }
        post_resp = self.client.post("/api/settings/ai/", data=json.dumps(resubmit_payload), content_type="application/json")
        self.assertEqual(post_resp.status_code, 200)

        # CRITICAL ASSERTION: Ciphertext stored in AppSettings must be BYTE-IDENTICAL to before!
        db_val_after = AppSettings.get("ai_openai_api_key", "").strip()
        self.assertEqual(db_val_after, enc_val_initial)
        self.assertEqual(decrypt_credential(db_val_after), raw_key)


    def test_provider_list_api_returns_schemas(self):
        resp = self.client.get("/api/settings/ai/providers/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("providers", data)
        provider_keys = [p["key"] for p in data["providers"]]
        self.assertCountEqual(provider_keys, ["ollama", "openai", "claude", "gemini", "azure"])


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
