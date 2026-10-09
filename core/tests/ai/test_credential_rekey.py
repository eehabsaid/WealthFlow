"""rekey_ai_keys: re-encrypt stored credentials from the default/old key to a private WEALTHFLOW_AI_ENCRYPTION_KEY."""

import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from core.models import AppSettings
from core.services.ai.credential_encryption import decrypt_credential, encrypt_credential, using_default_key
from core.services.ai.credential_rekey import rekey_all

NEW = "private_test_key_value_1234567890"


class RekeyTests(TestCase):
    def setUp(self):
        with patch.dict(os.environ, {"WEALTHFLOW_AI_ENCRYPTION_KEY": ""}):
            self.old_cipher = encrypt_credential("sk-secret")  # stored under the default key
        AppSettings.set("ai_openai_api_key", self.old_cipher)
        AppSettings.set("ai_model", "plain-value")

    def test_default_key_detection(self):
        with patch.dict(os.environ, {"WEALTHFLOW_AI_ENCRYPTION_KEY": ""}):
            self.assertTrue(using_default_key())
        with patch.dict(os.environ, {"WEALTHFLOW_AI_ENCRYPTION_KEY": NEW}):
            self.assertFalse(using_default_key())

    def test_dry_run_changes_nothing_apply_rewrites(self):
        with patch.dict(os.environ, {"WEALTHFLOW_AI_ENCRYPTION_KEY": NEW}):
            dry = rekey_all()
            self.assertEqual((dry["rewritten"], dry["applied"]), (1, False))
            self.assertEqual(AppSettings.get("ai_openai_api_key"), self.old_cipher)
            done = rekey_all(apply=True)
            self.assertEqual(done["rewritten"], 1)
            self.assertEqual(decrypt_credential(AppSettings.get("ai_openai_api_key")), "sk-secret")
            self.assertEqual(AppSettings.get("ai_model"), "plain-value")
            again = rekey_all(apply=True)
            self.assertEqual((again["rewritten"], again["already_current"]), (0, 1))

    def test_unreadable_rows_are_reported_and_untouched(self):
        AppSettings.set("ai_claude_api_key", "enc:not-a-real-token")
        with patch.dict(os.environ, {"WEALTHFLOW_AI_ENCRYPTION_KEY": NEW}):
            res = rekey_all(apply=True)
        self.assertEqual(res["unreadable"], ["ai_claude_api_key"])
        self.assertEqual(AppSettings.get("ai_claude_api_key"), "enc:not-a-real-token")

    def test_explicit_old_key(self):
        with patch.dict(os.environ, {"WEALTHFLOW_AI_ENCRYPTION_KEY": "older_private_key_abcdefghijklmnop"}):
            AppSettings.set("paymob_api_key", encrypt_credential("pm-key"))
        with patch.dict(os.environ, {"WEALTHFLOW_AI_ENCRYPTION_KEY": NEW}):
            res = rekey_all(old_secret="older_private_key_abcdefghijklmnop", apply=True)
            self.assertEqual(decrypt_credential(AppSettings.get("paymob_api_key")), "pm-key")
        self.assertEqual(res["unreadable"], ["ai_openai_api_key"])  # stored under the default key, not this old one

    def test_command_refuses_without_private_key_and_runs_with_it(self):
        with patch.dict(os.environ, {"WEALTHFLOW_AI_ENCRYPTION_KEY": ""}):
            with self.assertRaises(CommandError):
                call_command("rekey_ai_keys")
        out = StringIO()
        with patch.dict(os.environ, {"WEALTHFLOW_AI_ENCRYPTION_KEY": NEW}):
            call_command("rekey_ai_keys", "--apply", stdout=out)
            self.assertIn("Re-encrypted: 1", out.getvalue())

    def test_admin_banner_flag_in_ai_settings_payload(self):
        from core.views.settings.ai.ai_settings_get_helpers import build_ai_settings_get_payload

        with patch.dict(os.environ, {"WEALTHFLOW_AI_ENCRYPTION_KEY": ""}):
            self.assertTrue(build_ai_settings_get_payload()["encryption_key_default"])
        with patch.dict(os.environ, {"WEALTHFLOW_AI_ENCRYPTION_KEY": NEW}):
            self.assertFalse(build_ai_settings_get_payload()["encryption_key_default"])
