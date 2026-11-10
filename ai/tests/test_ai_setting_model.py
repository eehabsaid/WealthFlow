"""AISetting: global/per-user lookup, the "use general settings" switch and set()."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from ai.constants import USE_GENERAL_KEY, USER_LIMIT_KEY
from ai.models import AISetting


class AISettingModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("u1", password="x")

    def test_get_default_and_global(self):
        self.assertIsNone(AISetting.get("ai_model"))
        self.assertEqual(AISetting.get("ai_model", "d"), "d")
        AISetting.set("ai_model", "m1")
        self.assertEqual(AISetting.get("ai_model"), "m1")

    def test_set_updates_in_place(self):
        AISetting.set("ai_model", "a")
        AISetting.set("ai_model", "b")
        self.assertEqual(AISetting.objects.filter(key="ai_model").count(), 1)

    def test_per_user_row_wins_only_when_user_opted_out_of_general(self):
        AISetting.set("ai_model", "global")
        AISetting.set("ai_model", "mine", user=self.user)
        self.assertEqual(AISetting.get("ai_model", user=self.user), "global")   # default: general settings
        AISetting.set(USE_GENERAL_KEY, "false", user=self.user)
        self.assertEqual(AISetting.get("ai_model", user=self.user), "mine")
        AISetting.set(USER_LIMIT_KEY, "7", user=self.user)   # limit key is not a per-user-toggle key
        self.assertEqual(AISetting.get(USER_LIMIT_KEY, user=self.user), "7")
