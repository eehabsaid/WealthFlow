"""Per-user AI settings, token limits and token usage survive backup -> delete -> restore, next to the global rows
that share the same keys (AppSettings is unique on (key, owner))."""

import os
from ai.models import AISetting
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from ai.constants import DEFAULT_LIMIT_KEY, USE_GENERAL_KEY, USER_LIMIT_KEY
from ai.models.ai_conversation import AIConversation
from ai.models.ai_message import AIMessage
from ai.services.usage import effective_limit, limit_status, used_tokens


class AIUserSettingsBackupTests(TestCase):
    def test_round_trip_keeps_user_rows_global_rows_limits_and_usage(self):
        user = get_user_model().objects.create_user(username="bk_ai_user", password="Pw123456!")
        AISetting.set("ai_model", "global-model")
        AISetting.set(DEFAULT_LIMIT_KEY, "5000")
        AISetting.set("ai_model", "own-model", user=user)
        AISetting.set(USE_GENERAL_KEY, "false", user=user)
        AISetting.set(USER_LIMIT_KEY, "321", user=user)
        conv = AIConversation.objects.create(user=user, title="t")
        AIMessage.objects.create(conversation=conv, role="assistant", content="a", prompt_tokens=70, completion_tokens=30)
        before_used = used_tokens(user)

        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "ai.wfbackup")
            call_command("backup_data", output=tmp, filename="ai.wfbackup", no_compress=True)
            AISetting.objects.filter(key__in=["ai_model", DEFAULT_LIMIT_KEY, USE_GENERAL_KEY, USER_LIMIT_KEY]).delete()
            conv.delete()
            self.assertEqual(AISetting.objects.filter(key="ai_model").count(), 0)
            call_command("restore_data", path)
        finally:
            shutil.rmtree(tmp)

        self.assertEqual(AISetting.objects.get(key="ai_model", owner=None).value, "global-model")
        self.assertEqual(AISetting.objects.get(key="ai_model", owner=user).value, "own-model")
        self.assertEqual(AISetting.get(USE_GENERAL_KEY, user=user), "false")
        self.assertEqual(AISetting.get("ai_model", user=user), "own-model")   # own settings still apply
        self.assertEqual(AISetting.get(DEFAULT_LIMIT_KEY), "5000")
        self.assertEqual(effective_limit(user), 321)
        self.assertEqual(used_tokens(user), before_used)
        self.assertFalse(limit_status(user)["limited"])                          # own settings: unlimited
