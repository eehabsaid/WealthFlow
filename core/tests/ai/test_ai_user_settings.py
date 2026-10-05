import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.constants.ai_user_settings import DEFAULT_LIMIT_KEY, USE_GENERAL_KEY, USER_LIMIT_KEY
from core.models import AIConversation, AIMessage, AppSettings
from core.tests.billing.test_support import grant_ai_workspace_access
from core.services.ai.usage import MeteredProvider, TokenMeter, effective_limit, limit_status, used_tokens

User = get_user_model()
CHAT = "/api/financial-advisor/ai/chat/"


def _post(client, url, payload):
    return client.post(url, json.dumps(payload), content_type="application/json")


class AIUserSettingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="pw12345!")
        self.other = User.objects.create_user(username="other", password="pw12345!")
        self.admin = User.objects.create_user(username="boss", password="pw12345!", is_staff=True)
        from core.authentication.services import AuthWorkflowService
        profile = AuthWorkflowService.get_profile(self.admin)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_model", "general-model")

    def _own(self, **kw):
        for k, v in kw.items():
            AppSettings.set(k, v, user=self.user)

    # --- general-settings switch -------------------------------------------------
    def test_default_is_general_and_ignores_own_rows(self):
        self._own(ai_model="own-model")
        self.assertEqual(AppSettings.get("ai_model", user=self.user), "general-model")

    def test_own_settings_apply_when_switch_off(self):
        self._own(ai_model="own-model", **{USE_GENERAL_KEY: "false"})
        self.assertEqual(AppSettings.get("ai_model", user=self.user), "own-model")
        self.assertEqual(AppSettings.get("ai_model", user=self.other), "general-model")

    def test_me_post_never_writes_sysadmin_only_fields(self):
        self.client.force_login(self.user)
        res = _post(self.client, "/api/settings/ai/me/", {"use_general": False, "ai_provider": "ollama", "ai_permission_tier": "modify", "ai_read_only": False, "ai_multi_agent_enabled": True, "ai_ollama_url": "http://evil:1"})
        self.assertEqual(res.status_code, 200)
        for key in ("ai_permission_tier", "ai_read_only", "ai_multi_agent_enabled", "ai_ollama_url"):
            self.assertFalse(AppSettings.objects.filter(owner=self.user, key=key).exists(), key)

    # --- per-user API -------------------------------------------------------------
    def test_me_requires_login(self):
        self.assertEqual(self.client.get("/api/settings/ai/me/").status_code, 401)

    def test_me_get_exposes_no_sysadmin_fields(self):
        self.client.force_login(self.user)
        data = self.client.get("/api/settings/ai/me/").json()
        self.assertTrue(data["use_general"])
        for banned in ("ai_permission_tier", "ai_read_only", "ai_multi_agent_enabled", "ai_ollama_url", "ai_openai_base_url", "ai_azure_endpoint", "ai_pipeline_debug"):
            self.assertNotIn(banned, data["fields"])
        self.assertNotIn("azure", [p["key"] for p in data["providers_schema"]])

    def test_me_post_saves_own_and_flips_switch(self):
        self.client.force_login(self.user)
        with patch("core.views.settings.ai.ai_user_settings_views.run_ai_settings_connection_test", return_value=(True, None)):
            res = _post(self.client, "/api/settings/ai/me/", {"use_general": False, "ai_enabled": True, "ai_provider": "ollama", "ai_model": "mine", "ai_temperature": 0.3})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(AppSettings.get("ai_model", user=self.user), "mine")
        self.assertEqual(AppSettings.get("ai_model", user=self.other), "general-model")
        _post(self.client, "/api/settings/ai/me/", {"use_general": True})
        self.assertEqual(AppSettings.get("ai_model", user=self.user), "general-model")
        self.assertTrue(AppSettings.objects.filter(owner=self.user, key="ai_model", value="mine").exists())  # kept for switching back

    def test_me_post_rejects_azure_and_bad_values(self):
        self.client.force_login(self.user)
        self.assertEqual(_post(self.client, "/api/settings/ai/me/", {"use_general": False, "ai_provider": "azure"}).status_code, 400)
        self.assertEqual(_post(self.client, "/api/settings/ai/me/", {"use_general": False, "ai_provider": "ollama", "ai_temperature": 9}).status_code, 400)

    def test_secret_is_encrypted_and_masked(self):
        self.client.force_login(self.user)
        with patch("core.views.settings.ai.ai_user_settings_views.run_ai_settings_connection_test", return_value=(True, None)):
            _post(self.client, "/api/settings/ai/me/", {"use_general": False, "ai_provider": "openai", "ai_openai_api_key": "sk-secret-123456"})
        stored = AppSettings.objects.get(owner=self.user, key="ai_openai_api_key").value
        self.assertNotIn("sk-secret", stored)
        shown = self.client.get("/api/settings/ai/me/").json()["fields"]["ai_openai_api_key"]
        self.assertNotIn("sk-secret", shown)

    def test_shared_api_key_never_shown_to_a_member(self):
        from core.services.ai.credential_encryption import encrypt_credential
        AppSettings.set("ai_openai_api_key", encrypt_credential("sk-shared-ADMINKEY9876"))
        self.client.force_login(self.user)
        for use_general in (True, False):
            AppSettings.set(USE_GENERAL_KEY, "true" if use_general else "false", user=self.user)
            self.assertNotIn("9876", json.dumps(self.client.get("/api/settings/ai/me/").json()))

    # --- sysadmin limit ------------------------------------------------------------
    def test_limits_view_is_sysadmin_only(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/settings/ai/user-limits/").status_code, 403)
        self.assertEqual(_post(self.client, "/api/settings/ai/user-limits/", {"default_limit": 5}).status_code, 403)

    def test_limits_view_set_default_and_override(self):
        self.client.force_login(self.admin)
        self.assertEqual(_post(self.client, "/api/settings/ai/user-limits/", {"default_limit": 1000}).status_code, 200)
        self.assertEqual(effective_limit(self.user), 1000)
        _post(self.client, "/api/settings/ai/user-limits/", {"user_id": self.user.id, "limit": 50})
        self.assertEqual(effective_limit(self.user), 50)
        _post(self.client, "/api/settings/ai/user-limits/", {"user_id": self.user.id, "limit": 0})
        self.assertEqual(effective_limit(self.user), 0)  # explicit unlimited
        _post(self.client, "/api/settings/ai/user-limits/", {"user_id": self.user.id, "limit": ""})
        self.assertEqual(effective_limit(self.user), 1000)  # back to default
        self.assertEqual(_post(self.client, "/api/settings/ai/user-limits/", {"user_id": self.user.id, "limit": "abc"}).status_code, 400)
        self.assertEqual(_post(self.client, "/api/settings/ai/user-limits/", {"user_id": self.user.id, "limit": -3}).status_code, 400)
        rows = self.client.get("/api/settings/ai/user-limits/").json()["users"]
        self.assertTrue(any(r["username"] == "member" for r in rows))

    def test_user_cannot_write_limit_via_generic_settings_api(self):
        self.client.force_login(self.user)
        for body in ({USER_LIMIT_KEY: "0"}, {DEFAULT_LIMIT_KEY: "0"}, {USE_GENERAL_KEY: "false"}, {"ai_model": "sneaky"}):
            res = _post(self.client, "/api/settings/", body)
            self.assertEqual(res.status_code, 403, body)
        self.assertFalse(AppSettings.objects.filter(key__in=[USER_LIMIT_KEY, DEFAULT_LIMIT_KEY, USE_GENERAL_KEY, "ai_model"]).exclude(owner=None, key="ai_model").exists())

    # --- usage + enforcement ---------------------------------------------------------
    def _spend(self, tokens, user=None):
        conv = AIConversation.objects.create(user=user or self.user)
        AIMessage.objects.create(conversation=conv, role="assistant", content="x", prompt_tokens=tokens - 1, completion_tokens=1)

    def test_used_tokens_sums_month_for_user_only(self):
        self._spend(100)
        self._spend(40, user=self.other)
        self.assertEqual(used_tokens(self.user), 100)

    def test_limit_applies_only_on_general(self):
        AppSettings.set(DEFAULT_LIMIT_KEY, "100")
        self._spend(150)
        self.assertTrue(limit_status(self.user)["exceeded"])
        AppSettings.set(USE_GENERAL_KEY, "false", user=self.user)
        st = limit_status(self.user)
        self.assertFalse(st["exceeded"])
        self.assertFalse(st["limited"])

    def test_chat_blocked_when_exceeded_and_unblocked_on_own_settings(self):
        AppSettings.set(DEFAULT_LIMIT_KEY, "100")
        self._spend(150)
        grant_ai_workspace_access(self.user)
        AppSettings.set("ai_direct_answers", "false")
        self.client.force_login(self.user)
        provider = MagicMock()
        provider.supports_tools = True
        provider.generate.return_value = {"content": "ok", "tool_calls": None, "prompt_tokens": 7, "completion_tokens": 3, "error": None}
        with patch("core.views.ai_chat.ai_chat_core_views.get_active_ai_provider", return_value=provider):
            res = _post(self.client, CHAT, {"message": "hello"})
        self.assertEqual(res.json().get("error_key"), "ai_error_token_limit")
        provider.generate.assert_not_called()
        AppSettings.set(USE_GENERAL_KEY, "false", user=self.user)
        with patch("core.views.ai_chat.ai_chat_core_views.get_active_ai_provider", return_value=provider):
            res = _post(self.client, CHAT, {"message": "hello"})
        self.assertNotEqual(res.json().get("error_key"), "ai_error_token_limit")
        self.assertTrue(provider.generate.called)
        stamped = AIMessage.objects.filter(conversation__user=self.user, role="assistant").order_by("-id").first()
        self.assertEqual((stamped.prompt_tokens, stamped.completion_tokens), (7, 3))

    def test_meter_accumulates_and_ignores_non_dicts(self):
        meter = TokenMeter()
        inner = MagicMock()
        inner.generate.side_effect = [{"prompt_tokens": 10, "completion_tokens": 5}, {"prompt_tokens": None}, MagicMock()]
        mp = MeteredProvider(inner, meter)
        for _ in range(3):
            mp.generate("p")
        self.assertEqual((meter.prompt, meter.completion), (10, 5))
        self.assertIs(mp.model, inner.model)
