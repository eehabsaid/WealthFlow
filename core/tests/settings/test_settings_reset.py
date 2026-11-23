"""DELETE /api/settings/?key=... resets one PER-USER setting (removes only the caller's own row)."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AppSettings
from core.services.financial_advisor.commitments_calendar_service import resolve_week_start_day

User = get_user_model()
KEY = "commitments_week_start_day"
URL = "/api/settings/"


class SettingsResetTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="reset_a", password="x12345678")
        self.other = User.objects.create_user(username="reset_b", password="x12345678")
        self.client.login(username="reset_a", password="x12345678")

    def save(self, value):
        return self.client.post(URL, data=json.dumps({"key": KEY, "value": value}), content_type="application/json")

    def stored(self):
        return (self.client.get(URL).json()["settings"]).get(KEY)

    def test_reset_removes_the_stored_value_so_the_default_applies_again(self):
        self.save("3")
        self.assertEqual(self.stored(), "3")
        response = self.client.delete(f"{URL}?key={KEY}")
        self.assertEqual((response.status_code, response.json()["removed"]), (200, True))
        self.assertIsNone(self.stored())
        self.assertFalse(AppSettings.objects.filter(key=KEY, owner=self.user).exists())
        self.assertEqual(resolve_week_start_day(self.user), 0)

    def test_reset_of_an_unset_key_is_harmless(self):
        response = self.client.delete(f"{URL}?key={KEY}")
        self.assertEqual((response.status_code, response.json()["removed"]), (200, False))

    def test_other_users_value_is_untouched(self):
        AppSettings.set(KEY, "5", user=self.other)
        self.save("2")
        self.client.delete(f"{URL}?key={KEY}")
        self.assertEqual(AppSettings.get(KEY, user=self.other), "5")

    def test_platform_wide_keys_cannot_be_reset(self):
        AppSettings.set("available_languages", "en,ar")
        response = self.client.delete(f"{URL}?key=available_languages")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AppSettings.get("available_languages"), "en,ar")
        self.assertEqual(self.client.delete(URL).status_code, 400)

    def test_anonymous_is_rejected(self):
        self.client.logout()
        self.assertEqual(self.client.delete(f"{URL}?key={KEY}").status_code, 401)
