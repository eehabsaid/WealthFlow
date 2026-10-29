from django.test import SimpleTestCase
from unittest.mock import patch

from core.services.ai.context_builder_service.prompt import build_system_prompt


class ArabicResponseStyleTest(SimpleTestCase):
    @patch("core.services.shared.base_currency.get_user_base_code", return_value="EGP")
    @patch("core.services.ai.knowledge_engine.AIKnowledgeEngine.build_knowledge_context", return_value="")
    @patch("core.services.ai.memory.build_memory_block", return_value="")
    @patch("core.models.AppSettings.get", return_value="You are WealthFlow.")
    def test_system_prompt_requests_natural_egyptian_arabic(
        self, _settings, _memory, _knowledge, _currency
    ):
        prompt = build_system_prompt()
        self.assertIn("natural Egyptian Arabic (Masri)", prompt)
        self.assertIn("newsreader/newspaper language", prompt)
        self.assertIn("Do not add backslashes", prompt)
        self.assertIn("Keep financial terms and figures precise", prompt)
