"""Sysadmin API for the account-deletion grace period (Settings > Legal Text)."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.authentication.services import AuthWorkflowService
from core.constants.account_retention import GRACE_DAYS_KEY, grace_days
from core.models import AppSettings, AuthAuditLog

User = get_user_model()
URL = "/api/settings/account-retention/"


class AccountRetentionSettingsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="boss", password="pw12345")
        profile = AuthWorkflowService.get_profile(self.admin)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        self.member = User.objects.create_user(username="mem", password="pw12345")
        AuthWorkflowService.get_profile(self.member)

    def _post(self, value):
        return self.client.post(URL, data=json.dumps({"grace_days": value}), content_type="application/json")

    def test_get_returns_default_and_bounds(self):
        self.client.force_login(self.admin)
        data = self.client.get(URL).json()
        self.assertEqual(data, {"grace_days": 30, "default": 30, "min": 1, "max": 365})

    def test_post_saves_and_grace_days_follows(self):
        self.client.force_login(self.admin)
        res = self._post(14)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["grace_days"], 14)
        self.assertEqual(AppSettings.get(GRACE_DAYS_KEY), "14")
        self.assertEqual(grace_days(), 14)
        self.assertEqual(self._post("45").json()["grace_days"], 45)

    def test_invalid_values_rejected_and_nothing_changes(self):
        self.client.force_login(self.admin)
        for bad in (0, -5, 366, "abc", "", None, True, 1.5e9):
            self.assertEqual(self._post(bad).status_code, 400, bad)
        self.assertEqual(grace_days(), 30)
        self.assertIsNone(AppSettings.objects.filter(key=GRACE_DAYS_KEY).first())

    def test_non_sysadmin_and_anonymous_blocked(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.assertEqual(self._post(7).status_code, 403)
        self.assertEqual(grace_days(), 30)
        self.client.logout()
        self.assertIn(self.client.get(URL).status_code, (401, 403, 302))

    def test_change_is_audited_once(self):
        self.client.force_login(self.admin)
        self._post(10)
        self._post(10)
        rows = AuthAuditLog.objects.filter(event_type="account_grace_days_changed")
        self.assertEqual(rows.count(), 1)
        self.assertIn("from=30 to=10", rows.get().details)
