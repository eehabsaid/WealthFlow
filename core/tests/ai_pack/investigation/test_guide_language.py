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


class NoUserDataInTheGuideTest(SimpleTestCase):
    """The first Arabic guide answered some lines instead of translating them: "List the items and their estimated values" became
    "based on your data the items are: Gold Vault (87,500.00) ..." (the user's own balances inside a user guide)."""
    MD = "## Furniture\n\nInventory the furniture included within a property.\n\n1. Open the Furniture sub-tab.\n2. List the items and their estimated values.\n3. Save the inventory.\n"
    LEAK = "استنادًا إلى بياناتك، فإن العناصر هي: Gold Vault (87,500.00), Liquid Gold (25,000.00), Real Estate (175,000.00)."

    def test_amounts_that_are_not_in_the_source_are_found_in_every_script(self):
        from ai.services.investigation.compose_figures import invented_amounts

        self.assertTrue(invented_amounts("List the items.", self.LEAK))
        self.assertTrue(invented_amounts("List the items.", "المجموع ١٧٥٬٠٠٠٫٠٠"))
        self.assertFalse(invented_amounts("Pay 1,000.00 EGP.", "ادفع 1,000.00 جنيه."))
        self.assertFalse(invented_amounts("Step 1. Open in 2026.", "الخطوة 1. افتح في 2026."))

    def test_a_line_answered_instead_of_translated_never_reaches_the_guide(self):
        def ask(system, content, temperature=0.1):
            if "one line of a user guide" in system:
                return self.LEAK if "estimated values" in content else arabic(content)
            return content
        got = translate_markdown(ask, lambda: False, self.MD, "Arabic", 10**12, None, True)
        self.assertNotIn("87,500", got)
        self.assertNotIn("Gold Vault", got)
        self.assertIn("2. List the items and their estimated values.", got)   # stays the documented English line, never invented text

    def test_a_long_answer_to_a_short_line_is_refused(self):
        def ask(system, content, temperature=0.1):
            return " ".join(["كلمة"] * 40) if "one line of a user guide" in system and "estimated" in content else arabic(content)
        got = translate_markdown(ask, lambda: False, self.MD, "Arabic", 10**12, None, True)
        self.assertNotIn("كلمة كلمة كلمة", got)

    def test_a_short_name_is_translated_when_a_later_attempt_can(self):
        calls = []

        def ask(system, content, temperature=0.1):
            if "one line of a user guide" not in system:
                return content
            calls.append(temperature)
            return content if temperature < 0.3 else "إضافة فئة"
        got = translate_markdown(ask, lambda: False, "## Add Category\n", "Arabic", 10**12, None, True)
        self.assertIn("إضافة فئة", got)

    def test_an_english_title_left_in_a_translated_guide_is_localized(self):
        from ai.services.investigation.compose_title import with_app_name

        self.assertEqual(with_app_name("# WealthFlow User Guide\n\nنص\n", "", "Arabic").splitlines()[0], "# دليل مستخدم WealthFlow")
        self.assertEqual(with_app_name("# دليل WealthFlow\n\nنص\n", "", "Arabic").splitlines()[0], "# دليل WealthFlow")
        self.assertEqual(with_app_name("# Guide de l'utilisateur WealthFlow\n\ntexte\n", "", "French").splitlines()[0], "# Guide de l'utilisateur WealthFlow")
        self.assertEqual(with_app_name("# WealthFlow User Guide\n\ntext\n", "", "").splitlines()[0], "# WealthFlow User Guide")
