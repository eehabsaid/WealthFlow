"""A guide asked for in Arabic is never delivered in English: the language is read from the request itself (the model is only a last
resort and an unreadable answer is not "English"), and a piece the chunk translation cannot produce is translated line by line."""

from __future__ import annotations

from django.test import SimpleTestCase, TestCase

from ai.services.investigation.compose_language import named_languages, target_language, uses_latin_script
from ai.services.investigation.compose_translate import translate_markdown
from ai.views.ai_chat.chat_pipeline.investigate import ensure_document

from core.tests.ai_pack.investigation.support import make_user
from core.tests.ai_pack.investigation.test_compose_guide import Result
from core.tests.ai_pack.investigation.test_compose_translate import ASK_AR, MARK, TranslatingProvider, arabic

REAL_REQUEST = "generate a full user guide for the entire app as word, pdf, and html in well formatted Arabic"
NO_MODEL = lambda system, content, temperature=0: ""   # noqa: E731 - a model call that failed or returned nothing


class LanguageFromTheRequestTest(SimpleTestCase):
    def test_the_real_request_that_came_back_in_english(self):
        self.assertEqual(named_languages(REAL_REQUEST), ["Arabic"])
        self.assertEqual(target_language(NO_MODEL, REAL_REQUEST), "Arabic")   # no model needed, nothing can fall back to English

    def test_names_in_other_languages_and_spellings(self):
        for text, want in (("اعمل دليل المستخدم بالعربية", "Arabic"), ("اكتب الدليل بالعربي", "Arabic"), ("écris le guide en français", "French"),
                           ("Schreibe die Anleitung auf Deutsch", "German"), ("make the guide in Arabic please", "Arabic")):
            self.assertEqual(target_language(NO_MODEL, text), want, text)

    def test_english_is_named_or_implied(self):
        self.assertEqual(target_language(NO_MODEL, "اكتب الدليل بالانجليزي"), "")
        self.assertEqual(target_language(lambda s, c, t=0: "English", "write the user guide"), "")

    def test_a_request_written_in_arabic_without_a_named_language_gets_arabic(self):
        self.assertEqual(target_language(NO_MODEL, "اعمل لي دليل المستخدم للتطبيق كله"), "Arabic")

    def test_a_chatty_or_empty_model_answer_is_not_english(self):
        for reply in ("Arabic (Modern Standard Arabic)", "**Arabic**.", "The language is Arabic", "العربية"):
            self.assertEqual(target_language(lambda s, c, t=0, r=reply: r if "one word" in s else "YES", "write the guide in the language of Egypt"), "Arabic", reply)

    def test_known_scripts_need_no_model(self):
        self.assertFalse(uses_latin_script(NO_MODEL, "Arabic"))
        self.assertTrue(uses_latin_script(NO_MODEL, "French"))


class LineFallbackTest(SimpleTestCase):
    MD = "## Screen\n\nOpen the menu and click Save to keep your changes in the application today.\n\n1. Click Add.\n2. Enter the amount.\n\n- Login: Sign in securely.\n"

    def test_a_chunk_the_model_keeps_in_english_is_translated_line_by_line(self):
        def ask(system, content, temperature=0.1):
            return arabic(content) if "one line of a user guide" in system else content   # long replies come back unchanged, single lines work
        stats = {}
        got = translate_markdown(ask, lambda: False, self.MD, "Arabic", 10**12, None, True, stats)
        self.assertNotIn("Open the menu", got)
        self.assertEqual(stats["kept_english"], 0)
        self.assertIn("1. " + MARK, got)             # the step number is kept by the app
        self.assertIn("- " + MARK, got)
        self.assertTrue(got.startswith("## " + MARK))


class RealRequestTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("lang_admin", sysadmin=True)

    def guide(self, prov, ask):
        prov.user = self.admin
        res = Result()
        self.assertTrue(ensure_document(prov, ask, res, 24000, self.admin, None))
        return res.content

    def test_the_guide_is_translated_even_when_the_model_cannot_name_the_language(self):
        for answer in ("", "Arabic (MSA)", "I think it is Arabic, right?"):
            doc = self.guide(TranslatingProvider(language=answer), REAL_REQUEST)
            self.assertIn(MARK, doc, answer)
            self.assertNotIn("Open the screen from the menu", doc, answer)
            self.assertNotIn("## Dashboard", doc, answer)    # headings are translated too

    def test_a_guide_whose_chunk_translations_are_all_refused_is_still_arabic(self):
        class Stubborn(TranslatingProvider):
            def generate(self, messages, tools=None, **kwargs):
                system = messages[0]["content"]
                if "professional translator" in system:
                    return {"content": messages[-1]["content"], "completion_tokens": 10}   # returned unchanged
                if "one line of a user guide" in system:
                    return {"content": arabic(messages[-1]["content"]), "completion_tokens": 10}
                return super().generate(messages, tools, **kwargs)

        doc = self.guide(Stubborn(), ASK_AR)
        self.assertIn(MARK, doc)
        self.assertNotIn("## Dashboard", doc)
