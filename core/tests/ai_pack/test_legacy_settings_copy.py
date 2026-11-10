"""One-time copy of the ai_*/speech_*/image_gen_* AppSettings rows into AISetting (ai/legacy.py)."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from ai.legacy import MARKER_KEY, copy_legacy_settings
from ai.models import AISetting
from core.models import AppSettings


class LegacySettingsCopyTests(TestCase):
    def setUp(self):
        AISetting.objects.all().delete()
        self.user = get_user_model().objects.create_user("lc", password="x")
        AppSettings.objects.all().delete()
        AppSettings.objects.create(key="ai_model", value="old", description="d")
        AppSettings.objects.create(key="speech_voice", value="v")
        AppSettings.objects.create(key="ai_monthly_token_limit", value="5", owner=self.user)
        AppSettings.objects.create(key="app_name", value="WealthFlow")

    def test_copies_only_ai_families_and_keeps_old_rows(self):
        self.assertEqual(copy_legacy_settings(), 3)
        self.assertEqual(AISetting.get("ai_model"), "old")
        self.assertEqual(AISetting.objects.get(key="ai_monthly_token_limit").owner, self.user)
        self.assertFalse(AISetting.objects.filter(key="app_name").exists())
        self.assertEqual(AppSettings.objects.count(), 4)          # nothing removed or changed

    def test_runs_once_and_existing_new_values_win(self):
        AISetting.set("ai_model", "new")
        copy_legacy_settings()
        self.assertEqual(AISetting.get("ai_model"), "new")
        AppSettings.objects.create(key="ai_later", value="x")
        self.assertEqual(copy_legacy_settings(), 0)               # marker: not copied twice
        self.assertTrue(AISetting.objects.filter(key=MARKER_KEY).exists())
