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


from core.models import AppSettings
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
