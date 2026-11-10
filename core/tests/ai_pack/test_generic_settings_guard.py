"""WealthFlow's generic /api/settings/ must refuse AI keys for normal users (the AI app's keys now live in AISetting)."""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from ai.constants import DEFAULT_LIMIT_KEY, USE_GENERAL_KEY, USER_LIMIT_KEY
from ai.models import AISetting
from core.models import AppSettings


class GenericSettingsGuardTests(TestCase):
    def test_user_cannot_write_ai_keys_via_generic_settings_api(self):
        user = get_user_model().objects.create_user("plain", password="x")
        self.client.force_login(user)
        for body in ({USER_LIMIT_KEY: "0"}, {DEFAULT_LIMIT_KEY: "0"}, {USE_GENERAL_KEY: "false"}, {"ai_model": "sneaky"}):
            res = self.client.post("/api/settings/", json.dumps(body), content_type="application/json")
            self.assertEqual(res.status_code, 403, body)
        self.assertFalse(AISetting.objects.filter(key="ai_model").exists())
        self.assertFalse(AppSettings.objects.filter(key="ai_model", value="sneaky").exists())
