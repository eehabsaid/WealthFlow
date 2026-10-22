"""Screens split into parts (Settings has 20 tabs) and a one-word answer given in the user's language (an Arabic HTML request)."""

from __future__ import annotations

import json

from django.test import SimpleTestCase, TestCase

from core.services.ai.investigation.compose import compose_document
from core.services.ai.investigation.compose_descriptions import page_evidence
from core.services.ai.investigation.compose_sections import units
from core.services.ai.investigation.doc_path import yes_no

from .support import make_user
from .test_compose_guide import GuideProvider, Result

ARABIC_HTML = "اعمل لي دليل مستخدم للتطبيق بصيغة html"


class SplitPagesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("split_admin", sysadmin=True)

    def test_a_later_part_never_gets_the_other_tabs_as_page_level_dialogs(self):
        plan = [u for u in units(self.admin) if u["page"] == "Settings"]
        self.assertGreater(len(plan), 1)
        for unit in plan:
            shown = json.loads(unit["evidence"])
            for dialog in shown.get("dialogs") or []:
                name = dialog["name"] if isinstance(dialog, dict) else str(dialog)
                self.assertFalse(name.lower().startswith("settings "), name)   # "Settings Aiadvisor" is a tab id, not a dialog
            if unit["part"][0] > 1:
                self.assertNotIn("description", shown)   # the screen's own text belongs to its first part

    def test_page_evidence_excludes_every_tab_of_the_page(self):
        from core.services.ai.app_pages import app_pages

        all_tabs = [t["id"] for p in app_pages() if p["route"] == "settings" for t in p["tabs"]]
        later = page_evidence("settings", ["settings-banks"], all_tabs, first=False)
        self.assertEqual((later["items"], later["description"]), ([], None))
        first = page_evidence("settings", ["settings-banks"], all_tabs, first=True)
        self.assertFalse([i for i in first["items"] if i["name"].lower().startswith("settings ")])

    def test_no_chapter_of_the_guide_has_a_raw_id_heading_or_a_repeated_tab_text(self):
        res = Result()
        compose_document(GuideProvider(), "write the user guide as a word document", res, 24000, self.admin)
        heads = [ln for ln in res.content.splitlines() if ln.startswith("###")]
        self.assertFalse([h for h in heads if h.lower().startswith("### settings ")])


class OneWordAnswerTest(SimpleTestCase):
    def test_answers_in_any_supported_language(self):
        for word in ("YES", "yes.", "نعم", "نعم.", "Oui", "Ja", "Sí"):
            self.assertIs(yes_no(word), True, word)
        for word in ("NO", "لا", "Non", "Nein", "no."):
            self.assertIs(yes_no(word), False, word)
        for word in ("", "maybe", "هذا دليل"):
            self.assertIsNone(yes_no(word), word)


class ArabicHtmlRequestTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("html_admin", sysadmin=True)

    def test_a_yes_in_arabic_still_makes_the_app_write_the_html_guide(self):
        res = Result()
        text = compose_document(GuideProvider(about_app="نعم"), ARABIC_HTML, res, 24000, self.admin, strict=True)
        self.assertTrue(text.startswith("# "))
        self.assertGreater(text.count("\n## "), 5)

    def test_a_no_keeps_the_models_own_page_for_a_code_request(self):
        result = Result()
        result.content = '<!doctype html><form><input type="password"><button>Log in</button></form>'
        self.assertEqual(compose_document(GuideProvider(about_app="لا"), "write an html login page", result, 24000, self.admin, strict=True), "")


class DialogNameTest(SimpleTestCase):
    def test_a_numbered_dialog_key_is_one_dialog_with_a_clean_name(self):
        from core.services.ai.investigation.compose_descriptions import page_evidence

        names = [i["name"] for i in page_evidence("employment", [])["items"]]
        self.assertEqual(len(names), len(set(n.lower() for n in names)))
        self.assertFalse([n for n in names if n[-1:].isdigit()], names)

    def test_a_dialog_documented_under_an_interface_key_is_named_by_its_label(self):
        from core.services.ai.investigation.compose_descriptions import page_evidence

        names = [i["name"] for i in page_evidence("fixed-assets", ["assets"])["tabs"]["assets"]["items"]]
        self.assertNotIn("Documents Title", names)
        self.assertIn("Documents", names)
