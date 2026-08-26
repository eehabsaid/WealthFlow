import json
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import AppSettings

User = get_user_model()

class AIAdvisorInfrastructureTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="regular_user", password="password123")
        self.admin = User.objects.create_user(username="admin_user", password="password123", is_staff=True)

    def test_provider_factory(self):
        from core.integrations.ai_provider import (
            OllamaProvider,
            get_ai_provider,
            get_active_ai_provider,
            AVAILABLE_AI_PROVIDERS,
        )

        self.assertIn("ollama", AVAILABLE_AI_PROVIDERS)
        provider = get_ai_provider("ollama", base_url="http://localhost:11434", timeout=10)
        self.assertIsInstance(provider, OllamaProvider)
        self.assertEqual(provider.base_url, "http://localhost:11434")
        self.assertEqual(provider.timeout, 10)

        # Disabled by default
        AppSettings.set("ai_enabled", "false")
        self.assertIsNone(get_active_ai_provider())

        # Enabled
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_provider", "ollama")
        active = get_active_ai_provider()
        self.assertIsNotNone(active)
        self.assertEqual(active.PROVIDER_NAME, "ollama")

        # Unknown provider key returns None
        self.assertIsNone(get_ai_provider("invalid_provider"))

    @patch("urllib.request.urlopen")
    def test_ollama_provider_check_connection_success(self, mock_urlopen):
        from core.integrations.ai_provider import OllamaProvider

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"version": "0.1.30"}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        provider = OllamaProvider(base_url="http://localhost:11434", timeout=5)
        res = provider.check_connection()

        self.assertTrue(res["reachable"])
        self.assertEqual(res["version"], "0.1.30")
        self.assertIsNone(res["error"])
        self.assertGreaterEqual(res["response_time_ms"], 0)

    @patch("urllib.request.urlopen")
    def test_ollama_provider_list_models_and_check_available(self, mock_urlopen):
        from core.integrations.ai_provider import OllamaProvider

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "models": [
                {"name": "llama3.2:latest", "model": "llama3.2:latest", "size": 2000000000},
                {"name": "mistral:latest", "model": "mistral:latest", "size": 4000000000},
            ]
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        provider = OllamaProvider(base_url="http://localhost:11434")
        models = provider.list_models()
        self.assertEqual(len(models), 2)
        self.assertEqual(models[0]["name"], "llama3.2:latest")

        self.assertTrue(provider.check_model_available("llama3.2:latest"))
        self.assertTrue(provider.check_model_available("llama3.2"))
        self.assertFalse(provider.check_model_available("nonexistent_model"))

    @patch("urllib.request.urlopen")
    def test_ollama_provider_error_handling(self, mock_urlopen):
        from core.integrations.ai_provider import OllamaProvider

        mock_urlopen.side_effect = Exception("Connection refused")
        provider = OllamaProvider(base_url="http://localhost:11434")

        res = provider.check_connection()
        self.assertFalse(res["reachable"])
        self.assertIn("Connection refused", res["error"])

        models = provider.list_models()
        self.assertEqual(models, [])
        self.assertFalse(provider.check_model_available("llama3.2"))
