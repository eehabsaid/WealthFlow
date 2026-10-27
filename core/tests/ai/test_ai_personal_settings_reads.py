"""A user running on their own AI settings must have them honoured by the context budget,
history window, tool-result cap and Ollama sampling options (not just the general rows)."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.constants.ai_user_settings import USE_GENERAL_KEY
from core.integrations.ai_provider.ollama_options import build_options
from core.integrations.ai_provider.ollama_provider import OllamaProvider
from core.models import AppSettings
from core.services.ai.context_builder_service import ContextBuilderService
from core.services.ai.tools.result_budget import tool_result_max_chars

User = get_user_model()


class PersonalAISettingsReadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="pw12345!")
        AppSettings.set("ai_context_token_budget", "2048")
        AppSettings.set("ai_top_k", "40")
        AppSettings.set("ai_top_p", "0.9")
        AppSettings.set("ai_repeat_penalty", "1.1")
        for key, value in (
            ("ai_context_token_budget", "6000"),
            ("ai_top_k", "20"),
            ("ai_top_p", "0.5"),
            ("ai_repeat_penalty", "1.3"),
            (USE_GENERAL_KEY, "false"),
        ):
            AppSettings.set(key, value, user=self.user)

    def test_token_budget_follows_personal_value(self):
        self.assertEqual(ContextBuilderService().get_token_budget(self.user), 6000)
        self.assertEqual(ContextBuilderService().get_token_budget(), 2048)

    def test_tool_result_cap_follows_personal_value(self):
        self.assertEqual(tool_result_max_chars(self.user), 6000 * 4)
        self.assertEqual(tool_result_max_chars(), 2048 * 4)

    def test_ollama_sampling_options_follow_personal_values(self):
        provider = OllamaProvider.from_settings(user=self.user)
        options = build_options({}, provider.user_options)
        self.assertEqual(options["top_k"], 20)
        self.assertEqual(options["top_p"], 0.5)
        self.assertEqual(options["repeat_penalty"], 1.3)

    def test_ollama_sampling_options_use_general_when_switch_on(self):
        AppSettings.set(USE_GENERAL_KEY, "true", user=self.user)
        provider = OllamaProvider.from_settings(user=self.user)
        options = build_options({}, provider.user_options)
        self.assertEqual((options["top_k"], options["top_p"], options["repeat_penalty"]), (40, 0.9, 1.1))

    def test_call_kwargs_still_win_over_personal_values(self):
        provider = OllamaProvider.from_settings(user=self.user)
        options = build_options({"top_k": 5}, provider.user_options)
        self.assertEqual(options["top_k"], 5)
