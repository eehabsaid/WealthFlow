"""Guide structure: no invented sub-headings on screens without tabs, numbered chapters, a page per chapter (PDF and Word),
a compact PDF contents, and the refusal language for a request that mixes Arabic with Latin terms."""

import re
from io import BytesIO

import docx
import pypdf
from django.test import SimpleTestCase

from core.services.ai import scope_text
from core.services.ai.exports.builders import docx as docx_builder
from core.services.ai.exports.builders import pdf as pdf_builder
from core.services.ai.exports.builders.common import numbered_guide_blocks
from core.services.ai.investigation.compose_flatten import STYLE_RULE, dialog_names, flatten_untabbed
from core.services.ai.investigation.compose_sections import units
from core.tests.ai.test_guide_files_and_refusals import guide_markdown, make_doc

TEXT = "This page lets you manage the records of the application in a clear way for every user."


class FlattenTest(SimpleTestCase):
    UNIT = {"tab_items": [], "dialogs": ["Add Expense", "Import data"]}
    SECTION = "## Expenses\n\nPurpose text.\n\n### Overview\n\nIntro.\n\n### Main View\n\n1. Open.\n\n### Add Expense\n\n1. Press add.\n\n#### Steps\n\nmore\n"

    def test_invented_headings_are_dropped_and_documented_dialogs_become_dialog_level(self):
        out = flatten_untabbed(self.SECTION, self.UNIT)
        heads = [line for line in out.splitlines() if line.startswith("#")]
        self.assertEqual(heads, ["## Expenses", "#### Add Expense"])
        self.assertIn("Intro.", out)            # the text stays
        self.assertIn("1. Open.", out)

    def test_a_screen_with_tabs_is_left_alone(self):
        unit = {"tab_items": [{"name": "Accounts"}], "dialogs": []}
        self.assertEqual(flatten_untabbed(self.SECTION, unit), self.SECTION)

    def test_dialog_names_read_dicts_and_strings(self):
        self.assertEqual(dialog_names({"dialogs": [{"name": "A", "purpose": "x"}, "B", {"name": " "}]}), ["A", "B"])

    def test_the_style_rule_forbids_labels_and_tabless_subheadings(self):
        self.assertIn("without a label", STYLE_RULE)
        self.assertIn("no ### headings", STYLE_RULE)

    def test_every_unit_of_the_live_app_carries_its_dialog_names(self):
        class _Admin:
            is_authenticated = True
        from unittest.mock import patch

        with patch("core.authentication.utils.auth_utils.user_is_sysadmin", return_value=True):
            plan = units(_Admin())
        self.assertTrue(plan)
        self.assertTrue(all(isinstance(u["dialogs"], list) for u in plan))
        self.assertTrue(any(u["dialogs"] for u in plan))


class NumberingAndPagesTest(SimpleTestCase):
    def test_chapters_are_numbered_and_tabs_are_not(self):
        blocks = numbered_guide_blocks(make_doc(guide_markdown(TEXT, 3), "en"))
        chapters = [b.text for b in blocks if b.kind == "heading" and b.level == 2]
        self.assertEqual(chapters, ["1 Chapter 1", "2 Chapter 2", "3 Chapter 3"])
        self.assertEqual([b.text for b in blocks if b.kind == "heading" and b.level == 3][0], "Tab 1")

    def test_pdf_chapters_start_on_their_own_page_and_the_contents_stays_short(self):
        for lang in ("en", "ar"):
            reader = pypdf.PdfReader(BytesIO(pdf_builder._build(make_doc(guide_markdown(TEXT, 8), lang), lang)))
            self.assertGreaterEqual(len(reader.pages), 8 + 1, lang)          # contents + one page per chapter
            starts = [i for i, p in enumerate(reader.pages) if re.search(r"Chapter \d", p.extract_text() or "") and "Tab" in (p.extract_text() or "")]
            self.assertGreaterEqual(len(starts), 8, lang)

    def test_word_chapters_page_break_before_except_the_first(self):
        data = docx_builder._build(make_doc(guide_markdown(TEXT, 4), "en"), "en")
        chapters = [p for p in docx.Document(BytesIO(data)).paragraphs if p.style.name == "Heading 1"]
        self.assertEqual([p.paragraph_format.page_break_before for p in chapters], [False, True, True, True])
        self.assertEqual(chapters[0].text, "1 Chapter 1")


class RefusalLanguageTest(SimpleTestCase):
    def test_an_arabic_request_with_latin_terms_gets_the_arabic_refusal(self):
        self.assertEqual(scope_text.reply_language("اعمل لي دليل المستخدم للتطبيق بصيغة HTML مع صور PDF و Word"), "ar")
        self.assertEqual(scope_text.reply_language("اعمل دليل html"), "ar")

    def test_english_stays_english_and_french_is_untouched(self):
        self.assertEqual(scope_text.reply_language("write the user guide as an HTML file"), "en")
        self.assertEqual(scope_text.reply_language(""), "en")


class LongGuideContentsTest(SimpleTestCase):
    def test_a_guide_with_many_tabs_lists_only_chapters_in_the_contents_but_keeps_the_tabs_in_the_outline(self):
        md = "".join(f"## Screen {i}\n\n{TEXT}\n\n" + "".join(f"### Tab {i}-{j}\n\n{TEXT} {j}\n\n" for j in range(1, 7)) for i in range(1, 18))
        reader = pypdf.PdfReader(BytesIO(pdf_builder._build(make_doc(md, "en"), "en")))
        contents = [i for i, p in enumerate(reader.pages) if "Tab 1-1" in (p.extract_text() or "")]
        self.assertEqual(contents[0], 1)                   # page 0 is the contents; the first chapter starts on page 1 and has its tabs
        self.assertNotIn("Tab 3-2", reader.pages[0].extract_text())
        self.assertIn("Screen 17", reader.pages[0].extract_text())
        self.assertEqual(sum(len(o) for o in reader.outline if isinstance(o, list)), 17 * 6)
