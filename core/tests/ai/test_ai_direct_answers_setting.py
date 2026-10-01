"""ai_direct_answers toggle: default on, GET/POST round trip through the AI settings API, engine reads the same key."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AppSettings
from core.services.ai.query_engine import is_enabled

User = get_user_model()
URL = "/api/settings/ai/"


class DirectAnswersSettingTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="da_admin", password="password123", is_staff=True)
        from core.authentication.services import AuthWorkflowService

        profile = AuthWorkflowService.get_profile(self.admin)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        self.client.force_login(self.admin)

    def post(self, **body):
        return self.client.post(URL, json.dumps(body), content_type="application/json")

    def test_default_is_on(self):
        self.assertTrue(self.client.get(URL).json()["ai_direct_answers"])
        self.assertTrue(is_enabled(self.admin))

    def test_round_trip_off_then_on(self):
        self.assertEqual(self.post(ai_direct_answers=False).status_code, 200)
        self.assertFalse(self.client.get(URL).json()["ai_direct_answers"])
        self.assertEqual(AppSettings.get("ai_direct_answers"), "false")
        self.assertFalse(is_enabled(self.admin))
        self.assertEqual(self.post(ai_direct_answers=True).status_code, 200)
        self.assertTrue(self.client.get(URL).json()["ai_direct_answers"])
        self.assertTrue(is_enabled(self.admin))

    def test_omitting_the_key_keeps_the_stored_value(self):
        self.post(ai_direct_answers=False)
        self.post(ai_validate_mode="flag")
        self.assertFalse(self.client.get(URL).json()["ai_direct_answers"])

    def test_string_values_and_per_user_override(self):
        self.post(ai_direct_answers="false")
        self.assertFalse(self.client.get(URL).json()["ai_direct_answers"])
        AppSettings.set("ai_direct_answers", "true", user=self.admin)  # a per-user row wins over the global default
        self.assertTrue(is_enabled(self.admin))
