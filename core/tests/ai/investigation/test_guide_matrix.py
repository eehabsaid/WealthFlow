"""Near-duplicate removal and the Ask / Agent x English / Arabic quality matrix of the app guide (see compose_quality.py)."""

from __future__ import annotations

from django.test import SimpleTestCase, TestCase

from core.services.ai.investigation.compose_quality import report, sanitize
from core.services.ai.investigation.compose_sections import units
from core.views.ai_chat.chat_pipeline.investigate import ensure_document

from .support import make_user
from .test_compose_guide import ASK, Result
from .test_guide_quality import BadModel


class NearDuplicateTest(SimpleTestCase):
    BODY = "Open the Balance page and choose the Banks tab to add a new bank account with its opening balance and currency"

    def test_a_tab_written_twice_under_two_headings_is_kept_once(self):
        out = sanitize(f"## Balance\n\n### Bank accounts\n{self.BODY}.\n\n### Banks tab\n{self.BODY} today.\n\n### Interest\nRecord the interest the bank paid.\n")
        self.assertEqual(out.count(self.BODY), 1)
        self.assertIn("### Interest", out)

    def test_a_real_screen_or_tab_is_never_dropped_even_when_its_text_repeats_another(self):
        text = f"## Balance\n\n### Banks\n{self.BODY}.\n\n### Bank Interest\n{self.BODY} today.\n"
        out = sanitize(text, protect=frozenset({"banks", "bankinterest"}))
        self.assertEqual((out.count("### Banks"), out.count("### Bank Interest")), (1, 1))
        self.assertEqual(sanitize(f"## A\n\n{self.BODY}.\n\n## B\n\n{self.BODY}.\n").count("## "), 2)   # two chapters are never merged by their text

    def test_the_report_counts_what_is_wrong(self):
        from core.services.ai.investigation.compose_quality import report

        bad = "## A (1/2)\n\n### X\nt\n### X\nu. Run python manage.py go.\n\n## A\n\nv\n"
        found = report(bad)
        self.assertEqual((found["repeated_chapters"], found["repeated_sub_headings"], found["part_markers"]), (1, 1, 1))
        self.assertGreaterEqual(found["internals"], 1)
        self.assertEqual({k: v for k, v in report(sanitize(bad)).items() if k != "chapters"}, {"repeated_chapters": 0, "repeated_sub_headings": 0, "part_markers": 0, "internals": 0})


class QualityMatrixTest(TestCase):
    """Ask / Agent mode x English / Arabic: whatever the model did, the file is a clean guide that covers every screen."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("matrix_admin", sysadmin=True)

    def run_case(self, provider, ask, agent):
        res, provider.user = Result(), self.admin
        if agent:   # the model wrote its own file three times (three drafts)
            res.content = "Draft guide. " * 150
            res.steps = [{"tool": "generate_file", "status": "success", "arguments": {"content": "## Draft\n\n" + "text " * 80}} for _ in range(3)]
        self.assertTrue(ensure_document(provider, ask, res, 24000, self.admin, None))
        return res

    def check(self, res, arabic):
        doc = res.content
        found = report(doc)
        clean = {"repeated_chapters": 0, "repeated_sub_headings": 0, "part_markers": 0, "internals": 0}
        if arabic:   # the fake translator gives different titles one shared translation: only the markers and internals can be judged
            clean = {k: v for k, v in clean.items() if k in ("part_markers", "internals")}
        self.assertEqual({k: v for k, v in found.items() if k in clean}, clean)
        self.assertEqual(found["chapters"], len({u["page"] for u in units(self.admin)}))      # every screen, once
        self.assertFalse(any("content" in (s.get("arguments") or {}) for s in res.steps))     # the model's drafts are gone
        if arabic:
            self.assertTrue(any("\u0600" <= c <= "\u06ff" for c in doc))

    def test_ask_and_agent_in_english(self):
        for agent in (False, True):
            self.check(self.run_case(BadModel(), ASK, agent), arabic=False)

    def test_ask_and_agent_in_arabic(self):
        from .test_compose_translate import ASK_AR, TranslatingProvider

        for agent in (False, True):
            self.check(self.run_case(TranslatingProvider(), ASK_AR, agent), arabic=True)
