"""Translated guide clean-up: literal asterisks, a word written twice, a translation that loses numbered steps (and the log line
when a piece stays English)."""

from __future__ import annotations

import time

from django.test import SimpleTestCase

from core.services.ai.investigation.compose_polish import drop_doubled_words, numbered_steps, strip_emphasis
from core.services.ai.investigation.compose_translate import rejection, translate_markdown

LOGGER = "core.services.ai.investigation.compose_translate"
SOURCE = "## Plans\n\nPurpose of the page.\n\n1. Open the page now.\n2. Click the button here.\n3. Type the word to delete."
PROSE = "## الخطط\n\nالغرض من هذه الصفحة هو عرض الخطة وإدارتها.\n\nافتح الصفحة ثم اضغط على الزر واكتب الكلمة المطلوبة للحذف الآن."
STEPS = "## الخطط\n\nالغرض من هذه الصفحة هو عرض الخطة وإدارتها.\n\n1. افتح الصفحة الآن.\n2. اضغط على الزر هنا.\n3. اكتب الكلمة المطلوبة للحذف."


def run(replies, markdown=SOURCE, non_latin=True):
    calls = iter(replies)
    stats: dict = {}
    text = translate_markdown(lambda *a: next(calls, replies[-1]), lambda: False, markdown, "Arabic", time.monotonic() + 600, non_latin=non_latin, stats=stats)
    return text, stats


class PolishTests(SimpleTestCase):
    def test_single_asterisk_emphasis_removed(self):
        self.assertEqual(strip_emphasis("5. *نشر المعاملات ... الدخول*"), "5. نشر المعاملات ... الدخول")

    def test_bold_bullets_and_code_untouched(self):
        text = "**bold** and `a*b*c`\n* item *x*"
        self.assertEqual(strip_emphasis(text), "**bold** and `a*b*c`\n* item x")

    def test_doubled_word_removed(self):
        self.assertEqual(drop_doubled_words("تلك اللغة اللغة النشطة"), "تلك اللغة النشطة")

    def test_legitimate_repetitions_kept(self):
        for text in ("5 5 مرات", "(اللغة) اللغة", "اللغة، اللغة", "كلمة\nكلمة", "`ab ab ab`"):
            self.assertEqual(drop_doubled_words(text), text)

    def test_numbered_steps_counted_in_any_digits(self):
        self.assertEqual(numbered_steps("1. a\n 2) b\n٣. c\ntext 4. no"), 3)


class StepsTests(SimpleTestCase):
    def test_steps_rewritten_as_prose_rejected(self):
        self.assertEqual(rejection(SOURCE, PROSE, False, True), "numbered steps lost")

    def test_all_steps_kept_accepted(self):
        self.assertEqual(rejection(SOURCE, STEPS, False, True), "")

    def test_retry_after_prose_reply_keeps_steps(self):
        text, stats = run([PROSE, STEPS])
        self.assertEqual(numbered_steps(text), 3)
        self.assertEqual(stats["kept_english"], 0)

    def test_piece_that_keeps_failing_stays_english_with_a_log_line(self):
        with self.assertLogs(LOGGER, "WARNING") as logs:
            text, stats = run([PROSE])
        self.assertEqual(stats["kept_english"], 1)
        self.assertIn("1. Open the page now.", text)
        self.assertTrue(any("piece stayed English" in line for line in logs.output))

    def test_translation_is_cleaned(self):
        reply = STEPS.replace("اكتب الكلمة المطلوبة", "*اكتب الكلمة* الكلمة المطلوبة")
        text, _ = run([reply])
        self.assertNotIn("*", text)
        self.assertNotIn("الكلمة الكلمة", text)

    def test_doubled_word_kept_for_latin_alphabets(self):
        reply = "## Plans\n\nObjet de la page.\n\n1. Ouvrez la page.\n2. Nous nous connectons.\n3. Tapez le mot à supprimer."
        text, _ = run([reply], non_latin=False)
        self.assertIn("Nous nous connectons", text)
