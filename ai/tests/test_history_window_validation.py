from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from ai.constants import AI_HISTORY_WINDOW_MAX

User = get_user_model()


def _validate(data):
    from ai.views.settings.ai_settings_save_helpers import validate_ai_settings_post_data

    validated, error = validate_ai_settings_post_data(data)
    return validated, error


class HistoryWindowValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="pw12345!")

    def test_default_max_constant(self):
        self.assertEqual(AI_HISTORY_WINDOW_MAX, 100)

    def test_valid_window_accepted(self):
        validated, error = _validate({"ai_history_window": 10})
        self.assertIsNone(error)
        self.assertEqual(validated["history_window"], 10)

    def test_window_at_max_accepted(self):
        validated, error = _validate({"ai_history_window": AI_HISTORY_WINDOW_MAX})
        self.assertIsNone(error)
        self.assertEqual(validated["history_window"], AI_HISTORY_WINDOW_MAX)

    def test_window_above_max_rejected(self):
        validated, error = _validate({"ai_history_window": AI_HISTORY_WINDOW_MAX + 1})
        self.assertIsNone(validated)
        self.assertEqual(error.status_code, 400)
        self.assertIn(str(AI_HISTORY_WINDOW_MAX), error.content.decode())

    def test_window_zero_rejected(self):
        validated, error = _validate({"ai_history_window": 0})
        self.assertIsNone(validated)
        self.assertEqual(error.status_code, 400)


class HistoryWindowClampTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="pw12345!")

    def _build_context(self, stored_value):
        from ai.views.ai_chat.ai_chat_core_views import generation_pipeline as gp

        conversation = MagicMock()
        user_msg = MagicMock()
        user_msg.id = 1
        with patch.object(gp.AISetting, "get", return_value=stored_value), \
             patch.object(gp, "ContextBuilderService") as svc:
            svc.return_value.assemble_messages.return_value = ([], [])
            gp.build_context(MagicMock(), conversation, user_msg, "hello")
        # slicing length = .order_by(...)[ :N ] -> read the slice passed to __getitem__
        getitem = conversation.messages.filter.return_value.exclude.return_value.order_by.return_value.__getitem__
        return getitem.call_args[0][0].stop

    def test_in_range_value_used_as_is(self):
        self.assertEqual(self._build_context("10"), 10)

    def test_out_of_range_value_clamped_to_max(self):
        self.assertEqual(self._build_context("9999"), AI_HISTORY_WINDOW_MAX)

    def test_non_positive_value_falls_back_to_default(self):
        self.assertEqual(self._build_context("0"), 10)

    def test_invalid_value_falls_back_to_default(self):
        self.assertEqual(self._build_context("garbage"), 10)
