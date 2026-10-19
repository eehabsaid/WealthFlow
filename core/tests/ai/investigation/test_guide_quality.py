"""The guide never carries part markers, repeated headings or chapters, code or internals, or a stub where the app documents
more; a guide is always written by the app (also after a long answer or the model's own file); a document request lets the
model write up to the document output limit."""

from __future__ import annotations

import re

from django.test import SimpleTestCase, TestCase

from core.services.ai.investigation.compose_quality import blocks, clean_title, replace_blocks, sanitize, thin_tabs
from core.services.ai.investigation.compose_sections import tab_fallback, units
from core.services.ai.investigation.compose_translate import rejection
from core.views.ai_chat.chat_pipeline.investigate import document_write_tokens, ensure_document

from .support import make_user
from .test_compose_guide import ASK, GuideProvider, Result


class SanitizeTest(SimpleTestCase):
    def test_part_markers_leave_titles_and_headings(self):
        self.assertEqual(clean_title("Financial Advisor (1/3)"), "Financial Advisor")
        self.assertEqual(clean_title("الرصيد (٢/٣)"), "الرصيد")
        self.assertNotIn("(2/4)", sanitize("## Settings (2/4)\n\n### Banks (2/4)\n\ntext\n"))

    def test_a_sub_heading_written_twice_in_one_chapter_is_merged_but_two_chapters_may_share_one(self):
        text = "## Balance\n\n### Overview\nA.\n\nmore\n\n### Overview\nB.\n\n## Fixed Assets\n\n### Overview\nC.\n"
        out = sanitize(text)
        self.assertEqual(out.count("### Overview"), 2)           # once in Balance, once in Fixed Assets
        self.assertIn("A.", out)
        self.assertIn("B.", out)

    def test_a_chapter_written_twice_keeps_the_longer_one_but_different_chapters_with_one_title_stay(self):
        twice = "## Balance\n\nOpen the balance page and add a bank account.\n\n## Balance\n\nOpen the balance page and add a bank account today.\n"
        self.assertEqual(sanitize(twice).count("## Balance"), 1)
        different = "## Reports\n\nMonthly figures about spending categories.\n\n## Reports\n\nCertificates yield distribution and payout schedule.\n"
        self.assertEqual(sanitize(different).count("## Reports"), 2)

    def test_code_and_internals_never_reach_the_guide(self):
        text = ("## Settings\n\nSet WEALTHFLOW_AI_ENCRYPTION_KEY first. Then click Save.\n\n```\npython manage.py x\n```\n"
                "- Run python manage.py rekey_ai_keys --apply\n- Click Add.\n\nUse the `property_valuation_rate_map` table.\n")
        out = sanitize(text)
        for leaked in ("WEALTHFLOW_", "manage.py", "rekey_ai_keys", "property_valuation_rate_map", "```"):
            self.assertNotIn(leaked, out)
        self.assertIn("Then click Save.", out)
        self.assertIn("- Click Add.", out)

    def test_the_translated_text_is_not_judged_for_repeats(self):
        out = sanitize("## ترجمة\n\n### ترجمة\nأ\n\n### ترجمة\nب\n\n## ترجمة\n\nج\n", english=False)
        self.assertEqual(out.count("## ترجمة"), 2 + 2 + 0)       # nothing merged or dropped


class ThinTabTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("thin_admin", sysadmin=True)

    def test_a_stub_where_the_app_documents_more_is_replaced_by_the_documented_text(self):
        unit = next(u for u in units(self.admin) if "Currency Exchange" in u["tabs"])
        tab = next(t for t in unit["tab_items"] if t["name"] == "Currency Exchange")
        stub = f"## {unit['heading']}\n\n### Currency Exchange\n\nNo details are available for this tab.\n"
        self.assertEqual([t["name"] for t in thin_tabs(unit, stub, tab_fallback)], ["Currency Exchange"])
        fixed = replace_blocks(stub, [tab], tab_fallback)
        self.assertIn("Record and manage currency exchanges", fixed)
        self.assertNotIn("No details are available", fixed)
        self.assertEqual([name for name, _ in blocks(fixed)].count("currencyexchange"), 1)

    def test_a_full_text_is_never_replaced(self):
        unit = next(u for u in units(self.admin) if "Currency Exchange" in u["tabs"])
        tab = next(t for t in unit["tab_items"] if t["name"] == "Currency Exchange")
        full = "### Currency Exchange\n\n" + tab_fallback(tab).split("\n", 1)[1] + "\n\nExtra explanation."
        self.assertEqual(thin_tabs(unit, f"## X\n\n{full}", tab_fallback), [])


class BadModel(GuideProvider):
    """A model that echoes the part marker, repeats headings, leaks internals and writes stubs."""

    def generate(self, messages, tools=None, **kwargs):
        ask = messages[-1]["content"]
        if "Write ONLY this section" in ask:
            title = ask.split('Write ONLY this section: "', 1)[1].split('"', 1)[0]
            return {"content": f"## {title} (1/3)\n\n### Overview\nUse it.\n\n### Overview\nUse it again. Run python manage.py rekey_ai_keys --apply.\n"
                               "\n```\ncode\n```\n" + "Open the menu and click the tab to see your records on screen. " * 3}
        return super().generate(messages, tools, **kwargs)


class GuideCleanTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("clean_admin", sysadmin=True)

    def write(self, provider, content="Let me compose it."):
        res, provider.user = Result(), self.admin
        res.content = content
        self.assertTrue(ensure_document(provider, ASK, res, 24000, self.admin, None))
        return res.content

    def test_the_model_never_sees_a_part_marker_and_the_file_carries_none_of_its_mistakes(self):
        prov = BadModel()
        doc = self.write(prov)
        asked = "\n".join(c["ask"] for c in prov.calls)
        self.assertIsNone(re.search(r"\(\d+/\d+\)", asked))
        self.assertIsNone(re.search(r"\(\d+/\d+\)", doc))
        for leaked in ("manage.py", "rekey_ai_keys", "```"):
            self.assertNotIn(leaked, doc)
        chapters = re.split(r"(?m)^(?=## )", doc)
        for chapter in chapters:
            heads = [ln for ln in chapter.splitlines() if ln.startswith("### ")]
            self.assertEqual(len(heads), len(set(heads)), chapter[:60])

    def test_a_long_answer_without_a_file_is_still_replaced_by_the_apps_own_guide(self):
        doc = self.write(GuideProvider(), content="Here is a very long shallow guide. " * 80)
        self.assertTrue(doc.startswith("# WealthFlow user guide"))

    def test_a_report_on_the_users_data_keeps_the_models_text(self):
        res = Result()
        res.content = "Your spending report. " * 100
        prov = GuideProvider(about_app="NO")
        prov.user = self.admin
        self.assertFalse(ensure_document(prov, ASK, res, 24000, self.admin, None))
        self.assertEqual(res.content, "Your spending report. " * 100)


class WriteLimitTest(TestCase):
    def test_a_document_request_lets_the_model_write_up_to_the_document_limit(self):
        class P:
            user_options = {"context_size": 98304}
        self.assertGreater(document_write_tokens(P(), "write the user guide as a Word document") or 0, 4096)
        self.assertIsNone(document_write_tokens(P(), "what is my balance?"))


class RejectionReasonTest(SimpleTestCase):
    def test_a_rejection_names_its_reason_and_an_accepted_text_has_none(self):
        src = "## A\n\nOpen the menu and click Save to keep your changes in the application today.\n"
        self.assertEqual(rejection(src, "", False, True), "empty or much shorter than the source")
        self.assertEqual(rejection(src, src + "x", True, True), "cut off by the output limit")
        self.assertEqual(rejection(src, src.replace("A", "B"), False, True), "still mostly English (alphabet)")
