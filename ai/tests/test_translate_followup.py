"""Follow-up translation: "translate it to Arabic" turns the previous answer into a new answer in that language, with download links.
The model is a scripted fake: it answers the YES/NO and language questions and "translates" by swapping words for Arabic ones, so what is
tested is the app's own logic (when it triggers, what it checks, what it refuses to deliver)."""

import re
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from ai.integrations.ai_provider import OllamaProvider
from ai.models.ai_message import AIMessage
from ai.views.ai_chat.ai_chat_core_views.translate_stage import language_name, numbers_kept, numbers_of
import core.tests.ai_pack.qe_fixtures as fx

VIEW = "ai.views.ai_chat.ai_chat_core_views"
GP = f"{VIEW}.generation_pipeline.build_context"
NO_LLM = patch.object(OllamaProvider, "generate", side_effect=AssertionError("LLM must not be called"))
WORD = re.compile(r"[A-Za-z]{3,}")


def arabic(text):
    return WORD.sub("كلمة", text)


def scripted(*, is_translation="YES", language="Arabic", translate=arabic, story="Once upon a time there was a lucky coin."):
    seen = []

    def generate(messages, **kw):
        system, user = messages[0]["content"], messages[-1]["content"]
        seen.append(system[:40])
        if "translate the previous answer" in system:
            text = is_translation
        elif "English name of the language the request" in system:
            text = language
        elif "normally written in the Latin alphabet" in system:
            text = "NO"
        elif "professional translator" in system:
            text = translate(user)
        else:
            text = story
        return {"content": text, "tool_calls": None, "error": None, "completion_tokens": 10}

    prov = MagicMock()
    prov.supports_tools = False
    prov.generate.side_effect = generate
    prov.seen = seen
    return prov


def run(test, prov, text, conversation=True):
    ctx = ([{"role": "system", "content": "SYS"}, {"role": "user", "content": "q"}], ["balance"])
    with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), patch(GP, return_value=ctx):
        return fx.ask(test, text, conversation=conversation)["message"]


class TranslateFollowupTests(TestCase):
    def setUp(self):
        fx.build(self)
        with NO_LLM:
            self.first = fx.ask(self, "list the paid salaries for year 2026")["message"]

    def test_the_previous_answer_is_translated_with_its_numbers_and_gets_links_to_the_new_answer(self):
        reply = run(self, scripted(), "translate it to Arabic")
        self.assertEqual(reply["tool_calls"][0]["tool"], "translate_followup")
        self.assertTrue(reply["tool_calls"][0]["complete"])
        self.assertIn("كلمة", reply["content"])
        self.assertTrue(numbers_kept(self.first["content"], reply["content"]))
        self.assertIn("87,643.86", reply["content"])
        ids = {int(i) for i in re.findall(r"/messages/(\d+)/export/", reply["content"])}
        self.assertEqual(ids, {reply["id"]})            # the NEW answer is what the links export
        self.assertEqual(AIMessage.objects.get(pk=self.first["id"]).content, self.first["content"])   # the original stays as it was

    def test_a_named_format_limits_the_links(self):
        reply = run(self, scripted(), "translate it to Arabic as word")
        self.assertEqual(re.findall(r"/export/(\w+)/", reply["content"]), ["docx"])

    def test_a_translation_that_changes_a_number_is_never_delivered(self):
        reply = run(self, scripted(translate=lambda t: arabic(t).replace("87,643.86", "87,000")), "translate it to Arabic")
        self.assertFalse(reply["tool_calls"][0]["complete"])
        self.assertNotIn("/export/", reply["content"])
        self.assertIn("could not translate", reply["content"])

    def test_text_that_stays_untranslated_is_never_delivered(self):
        reply = run(self, scripted(translate=lambda t: t), "translate it to Arabic")
        self.assertFalse(reply["tool_calls"][0]["complete"])
        self.assertNotIn("/export/", reply["content"])

    def test_not_a_translation_request_goes_on_to_the_normal_pipeline(self):
        prov = scripted(is_translation="NO")
        reply = run(self, prov, "tell me a short story about a lucky coin")
        self.assertIn("lucky coin", reply["content"])
        self.assertNotEqual((reply["tool_calls"] or [{}])[0].get("tool"), "translate_followup")

    def test_a_message_without_a_named_language_is_not_a_translation(self):
        reply = run(self, scripted(language="NONE"), "translate it please")
        self.assertNotEqual((reply["tool_calls"] or [{}])[0].get("tool"), "translate_followup")

    def test_an_instant_data_question_after_an_answer_costs_no_model_call(self):
        with NO_LLM as gen:
            again = fx.ask(self, "list the paid salaries for year 2026")["message"]
            gen.assert_not_called()
        self.assertIn("87,643.86", again["content"])

    def test_nothing_to_translate_in_a_new_conversation(self):
        prov = scripted()
        reply = run(self, prov, "translate it to Arabic", conversation=False)
        self.assertNotEqual((reply["tool_calls"] or [{}])[0].get("tool"), "translate_followup")
        self.assertFalse(any("translate the previous answer" in s for s in prov.seen))


class TranslateHelpersTests(SimpleTestCase):
    def test_numbers_are_compared_across_digit_styles_and_separators(self):
        self.assertEqual(numbers_of("1,234.50 EGP on 2026"), {"123450", "2026"})
        self.assertTrue(numbers_kept("Total 1,234.50 in 2026", "المجموع ١٬٢٣٤٫٥٠ في ٢٠٢٦"))
        self.assertTrue(numbers_kept("Total 1,234.50", "Total 1.234,50"))
        self.assertFalse(numbers_kept("Total 1,234.50", "Total 1,234.00"))
        self.assertFalse(numbers_kept("Paid 100 and 200", "Paid 100"))

    def test_language_name_accepts_only_a_language_word(self):
        ask = lambda reply: (lambda system, content, temperature=0: reply)  # noqa: E731
        self.assertEqual(language_name(ask("Arabic."), "x"), "Arabic")
        for bad in ("NONE", "", "I think it is Arabic or French maybe", "42", "Ar4bic"):
            self.assertEqual(language_name(ask(bad), "x"), "", bad)
