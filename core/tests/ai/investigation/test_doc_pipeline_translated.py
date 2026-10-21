"""Translated-guide alignment, title and contents-list guard (see test_doc_pipeline_fixes.py for the rest)."""

from __future__ import annotations

from django.test import SimpleTestCase

from core.services.ai.investigation.compose_align import align_to_source
from core.services.ai.investigation.compose_contents import drop_contents
from core.services.ai.investigation.compose_quality import report, sanitize
from core.services.ai.investigation.compose_title import guide_title, with_app_name

SOURCE = "# WealthFlow user guide\n\nIntro.\n\n## Balance\n\n### Banks\n\nbank text one two three four\n\n### Currencies\n\ncurrency text five six\n\n## Expenses\n\n### List\n\nlist text seven eight\n"


class TranslatedGuideTest(SimpleTestCase):
    def test_a_repeated_chapter_and_sub_heading_are_removed_by_position(self):
        ar = ("# دليل WealthFlow\n\nمقدمة.\n\n## الرصيد\n\n### البنوك\n\nنص البنك واحد اثنان\n\n### البنوك\n\nنص البنك واحد اثنان ثلاثة\n\n### العملات\n\nنص العملات\n\n"
              "## الرصيد\n\n### البنوك\n\nنص البنك واحد اثنان\n\n## المصروفات\n\n### القائمة\n\nنص القائمة\n")
        out_text = sanitize(ar, english=False, source=SOURCE)
        found = report(out_text)
        self.assertEqual((found["chapters"], found["repeated_chapters"], found["repeated_sub_headings"]), (2, 0, 0))
        self.assertEqual(out_text.count("### العملات"), 1)

    def test_a_flattened_heading_level_is_restored_and_no_real_section_is_dropped(self):
        src = "## Assets\n\n### Assets\n\nintro text\n\n#### General\n\ng text one two\n\n#### Gold Details\n\ngold text\n\n#### Details\n\nd text\n\n## B\n\ntext\n"
        ar = src.replace("####", "###").replace("General", "عام").replace("Gold Details", "تفاصيل الذهب").replace("Details", "التفاصيل")
        out_text = align_to_source(src, ar)
        self.assertEqual(out_text.count("#### "), 3)
        self.assertIn("تفاصيل الذهب", out_text)
        self.assertIn("التفاصيل", out_text)

    def test_same_structure_is_untouched_even_with_identical_translations(self):
        same = SOURCE.replace("Balance", "X").replace("Expenses", "X")
        self.assertEqual(align_to_source(SOURCE, same).strip(), same.strip())

    def test_title_names_the_app(self):
        self.assertTrue(guide_title("# Personal Finance and Asset Management App User Guide\n\nHello there.").startswith("# WealthFlow user guide"))
        self.assertTrue(guide_title("# WealthFlow handbook\n\nHi.").startswith("# WealthFlow handbook"))
        self.assertTrue(guide_title("no title, just text").startswith("# WealthFlow user guide"))
        self.assertIn("WealthFlow", with_app_name("# دليل المستخدم\n\nنص\n", SOURCE).splitlines()[0])
        self.assertEqual(with_app_name("# دليل WealthFlow\n\nنص\n", SOURCE).splitlines()[0], "# دليل WealthFlow")


class ContentsGuardTest(SimpleTestCase):
    def test_a_mirroring_list_and_a_paged_list_are_dropped(self):
        md = ("# G\n\n## Contents\n\n- Balance\n- Expenses\n- Assets\n- Settings\n\n## Balance\n\nText about balance here.\n\n## Expenses\n\nText.\n\n## Assets\n\nText.\n\n## Settings\n\nText.\n")
        out_text = drop_contents(md)
        self.assertNotIn("## Contents", out_text)
        self.assertNotIn("- Assets", out_text)
        paged = "## A\n\nIntro.\n\n1. Setup ........ 3\n2. Usage ........ 5\n3. Tips ........ 9\n\n## B\n\nText.\n"
        self.assertNotIn("........", drop_contents(paged))

    def test_a_chapter_listing_its_own_tabs_is_ordinary_text(self):
        md = "## Balance\n\nTabs:\n\n- Banks\n- Currencies\n- Rates\n- Gold\n\n### Banks\n\nx\n\n### Currencies\n\ny\n\n### Rates\n\nz\n\n### Gold\n\nw\n\n## Expenses\n\nText.\n"
        self.assertEqual(drop_contents(md), md)
