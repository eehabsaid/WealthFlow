import json
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import AppSettings

User = get_user_model()

class AIAdvisorViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="regular_user", password="password123")
        self.admin = User.objects.create_user(username="admin_user", password="password123", is_staff=True)

    def test_ai_provider_list_view_permissions(self):
        # Unauthenticated / Regular user forbidden
        self.client.force_login(self.user)
        res = self.client.get("/api/settings/ai/providers/")
        self.assertEqual(res.status_code, 403)

        # Admin user allowed
        self.client.force_login(self.admin)
        res = self.client.get("/api/settings/ai/providers/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("providers", data)
        self.assertTrue(any(p["key"] == "ollama" for p in data["providers"]))

    def test_ai_settings_view_get_post_and_validations(self):
        self.client.force_login(self.admin)

        # GET settings
        res = self.client.get("/api/settings/ai/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("ai_enabled", data)
        self.assertIn("ai_provider", data)
        self.assertIn("ai_ollama_url", data)
        self.assertIn("ai_model", data)
        self.assertIn("ai_temperature", data)
        self.assertIn("ai_context_size", data)
        self.assertIn("ai_timeout", data)
        self.assertIn("ai_system_prompt", data)
        self.assertIn("ai_max_tokens", data)
        self.assertIn("ai_top_p", data)
        self.assertIn("ai_top_k", data)
        self.assertIn("ai_repeat_penalty", data)

        # POST invalid provider
        res_bad_prov = self.client.post(
            "/api/settings/ai/",
            json.dumps({"ai_provider": "invalid_provider"}),
            content_type="application/json",
        )
        self.assertEqual(res_bad_prov.status_code, 400)

        # POST invalid temperature (> 2.0)
        res_bad_temp = self.client.post(
            "/api/settings/ai/",
            json.dumps({"ai_temperature": 3.5}),
            content_type="application/json",
        )
        self.assertEqual(res_bad_temp.status_code, 400)

        # POST valid settings
        payload = {
            "ai_enabled": True,
            "ai_provider": "ollama",
            "ai_ollama_url": "http://localhost:11434",
            "ai_model": "llama3.2:latest",
            "ai_temperature": 0.5,
            "ai_context_size": 8192,
            "ai_timeout": 20,
            "ai_system_prompt": "Custom prompt",
            "ai_max_tokens": 1024,
            "ai_top_p": 0.8,
            "ai_top_k": 30,
            "ai_repeat_penalty": 1.05,
            "ai_seed": "12345",
            "ai_keep_alive": "10m",
        }
        res_valid = self.client.post(
            "/api/settings/ai/",
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res_valid.status_code, 200)

        # Verify saved in AppSettings
        self.assertEqual(AppSettings.get("ai_enabled"), "true")
        self.assertEqual(AppSettings.get("ai_temperature"), "0.5")
        self.assertEqual(AppSettings.get("ai_context_size"), "8192")
        self.assertEqual(AppSettings.get("ai_timeout"), "20")

    @patch("urllib.request.urlopen")
    def test_ai_connection_test_view(self, mock_urlopen):
        self.client.force_login(self.admin)

        # Mock /api/version and /api/tags
        def side_effect(req, timeout=15):
            url = req.full_url
            mock_resp = MagicMock()
            if "/api/version" in url:
                mock_resp.read.return_value = json.dumps({"version": "0.1.30"}).encode("utf-8")
            elif "/api/tags" in url:
                mock_resp.read.return_value = json.dumps({
                    "models": [{"name": "llama3.2:latest", "model": "llama3.2:latest"}]
                }).encode("utf-8")
            mock_resp.__enter__.return_value = mock_resp
            return mock_resp

        mock_urlopen.side_effect = side_effect

        res = self.client.post(
            "/api/settings/ai/test-connection/",
            json.dumps({
                "provider": "ollama",
                "base_url": "http://localhost:11434",
                "model": "llama3.2:latest",
                "timeout": 10,
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["reachable"])
        self.assertEqual(data["version"], "0.1.30")
        self.assertTrue(data["model_available"])
        self.assertGreaterEqual(data["response_time_ms"], 0)
        self.assertEqual(len(data["models"]), 1)
