import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.authentication.services import AuthWorkflowService
from core.authentication.services.member_role import assign_member_role
from core.authentication.utils.auth_utils import get_user_allowed_pages
from core.models import AppSettings, PagePermission

User = get_user_model()

SECRET_KEYS = ("smtp_password", "ai_openai_api_key", "paymob_hmac_secret", "paymob_api_key")


def _post(client, payload):
    return client.post("/api/settings/", data=json.dumps(payload), content_type="application/json")


class SettingsAccessTests(TestCase):
    def setUp(self):
        AppSettings.set("smtp_host", "smtp.example.com")
        AppSettings.set("smtp_username", "mailer")
        AppSettings.set("smtp_password", "hunter2")
        AppSettings.set("ai_openai_api_key", "sk-secret")
        AppSettings.set("paymob_api_key", "pm-secret")
        AppSettings.set("paymob_hmac_secret", "hmac-secret")
        AppSettings.set("available_languages", '[{"code": "en"}]')
        self.member = User.objects.create_user(username="member1", password="pw12345")
        assign_member_role(self.member)
        self.admin = User.objects.create_user(username="sysadmin1", password="pw12345")
        profile = AuthWorkflowService.get_profile(self.admin)
        profile.is_sysadmin = True
        profile.save()

    def _settings(self, user):
        self.client.force_login(user)
        return self.client.get("/api/settings/").json()["settings"]

    def test_member_gets_whitelist_only(self):
        settings = self._settings(self.member)
        self.assertIn("available_languages", settings)
        for key in ("smtp_host", "smtp_username", "sender_email", *SECRET_KEYS):
            self.assertNotIn(key, settings)
        self.assertFalse([k for k in settings if k.startswith(("smtp_", "ai_", "paymob_"))])

    def test_no_secret_value_is_ever_returned(self):
        for user in (self.member, self.admin):
            body = json.dumps(self._settings(user))
            for secret in ("hunter2", "sk-secret", "pm-secret", "hmac-secret"):
                self.assertNotIn(secret, body)

    def test_admin_sees_is_set_flags_for_secrets(self):
        settings = self._settings(self.admin)
        self.assertEqual(settings["smtp_host"], "smtp.example.com")
        self.assertEqual(settings["smtp_password_is_set"], "true")
        self.assertEqual(settings["paymob_api_key_is_set"], "true")
        self.assertNotIn("smtp_password", settings)

    def test_member_cannot_write_global_keys(self):
        self.client.force_login(self.member)
        self.assertEqual(_post(self.client, {"key": "smtp_host", "value": "evil.example"}).status_code, 403)
        self.assertEqual(AppSettings.get("smtp_host"), "smtp.example.com")

    def test_forbidden_key_blocks_whole_batch(self):
        self.client.force_login(self.member)
        res = _post(self.client, {"settings": {"dashboard_show_certs": "false", "smtp_host": "evil"}})
        self.assertEqual(res.status_code, 403)
        self.assertIsNone(AppSettings.objects.filter(key="dashboard_show_certs", owner=self.member).first())

    def test_member_can_write_own_scoped_keys(self):
        self.client.force_login(self.member)
        self.assertEqual(_post(self.client, {"key": "dashboard_show_certs", "value": "false"}).status_code, 200)

    def test_email_templates_tab_is_sysadmin_only_by_default(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get("/api/settings/email-templates/").status_code, 403)
        self.assertEqual(self.client.post("/api/settings/email-test/").status_code, 403)
        self.assertNotIn("settings_emailtemplates", get_user_allowed_pages(self.member))
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/api/settings/email-templates/").status_code, 200)

    def test_explicit_grant_unlocks_email_templates_and_smtp_keys(self):
        PagePermission.objects.create(user=self.member, page="settings_emailtemplates", granted=True)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get("/api/settings/email-templates/").status_code, 200)
        self.assertEqual(_post(self.client, {"key": "smtp_host", "value": "new.example"}).status_code, 200)
        settings = self.client.get("/api/settings/").json()["settings"]
        self.assertEqual(settings["smtp_password_is_set"], "true")
        self.assertNotIn("smtp_password", settings)
