"""Direct Answers OFF: the model path must be handed the exact computed rows (not just the capped summary),
so a list question is answered completely and the validator has the figures to check against."""

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from core.models import AppSettings
from core.services.ai.query_engine import verified_for_model
from . import qe_fixtures as fx

GP = "core.views.ai_chat.ai_chat_core_views.generation_pipeline.build_context"
VIEW = "core.views.ai_chat.ai_chat_core_views"
SUMMARY_ONLY = ([{"role": "system", "content": "SYS === FINANCIAL CONTEXT DATA === salary summary: 8 entries"},
                 {"role": "user", "content": "q"}], ["salary"])


def model():
    prov = MagicMock()
    prov.supports_tools = False
    prov.generate.side_effect = lambda *a, **k: {"content": "ok", "tool_calls": None, "error": None}
    return prov


class VerifiedDataTests(TestCase):
    def setUp(self):
        fx.build(self)

    def sent_to_model(self, question):
        AppSettings.set("ai_direct_answers", "false")
        prov = model()
        with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), \
                patch(GP, side_effect=lambda *a, **k: ([dict(m) for m in SUMMARY_ONLY[0]], list(SUMMARY_ONLY[1]))):
            fx.ask(self, question, conversation=False)
        self.assertTrue(prov.generate.called)
        return "\n".join(str(m.get("content")) for m in prov.generate.call_args_list[0][0][0])

    def test_salary_list_reaches_the_model_with_every_row_and_total(self):
        sent = self.sent_to_model("please list the paid salaries for year 2026")
        self.assertIn("VERIFIED DATA", sent)
        self.assertIn("87,643.86", sent)
        self.assertIn("Grand Total", sent)

    def test_same_with_a_file_request_and_in_other_languages(self):
        for question in ("اعرض رواتب 2026", "liste mes salaires 2026"):
            with self.subTest(question=question):
                self.assertIn("87,643.86", self.sent_to_model(question))

    def test_a_file_request_is_answered_without_the_model_even_while_instant_answers_are_off(self):
        """Export is its own feature: the router's exact rows + the file, 0 LLM calls (see engine.answer force=True)."""
        AppSettings.set("ai_direct_answers", "false")
        prov = model()
        with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), patch(GP, return_value=SUMMARY_ONLY):
            data = fx.ask(self, "list my salaries 2026 and export it in excel", conversation=False)
        self.assertFalse(prov.generate.called)
        self.assertIn("87,643.86", data["message"]["content"])
        self.assertIn("/export/xlsx/", data["message"]["content"])

    def test_other_topics_get_their_rows_too(self):
        self.assertIn("VERIFIED DATA", self.sent_to_model("list my expenses for June 2026"))

    def test_no_verified_block_when_the_router_cannot_answer(self):
        self.assertNotIn("VERIFIED DATA", self.sent_to_model("tell me a joke about money"))

    def test_nothing_is_added_when_direct_answers_is_on(self):
        AppSettings.set("ai_direct_answers", "true")
        prov = model()
        with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), patch(GP, return_value=SUMMARY_ONLY):
            data = fx.ask(self, "please list the paid salaries for year 2026", conversation=False)
        self.assertFalse(prov.generate.called)  # answered instantly, no model call
        self.assertIn("87,643.86", data["message"]["content"])

    def test_function_edges(self):
        self.assertIsNone(verified_for_model(AnonymousUser(), "list salaries 2026"))
        self.assertIsNone(verified_for_model(None, "list salaries 2026"))
        self.assertIsNone(verified_for_model(self.user, "tell me a joke"))
        info = {}
        text = verified_for_model(self.user, "list the paid salaries for year 2026", info=info)
        self.assertTrue(text.startswith("VERIFIED DATA"))
        self.assertEqual(info["verified_data"]["capability"], "salary")
