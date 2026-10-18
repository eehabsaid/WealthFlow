"""The guide is written from each screen's DOCUMENTED text (looked up by key), one chapter per screen, once per document:
Agent mode no longer lets the model's own drafts into the file, repeated drafts are never joined, an English guide gets
English labels, and the instructions tell the model not to invent or to talk about its sources."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.test import SimpleTestCase, TestCase

from core.services.ai.agent.instructions import DEFAULT_DOCUMENT_INSTRUCTIONS, DEFAULT_INSTRUCTIONS
from core.services.ai.exports.doc_language import document_language
from core.services.ai.exports.full_data import from_tool_calls, superseded_drafts
from core.services.ai.investigation.compose import drop_model_drafts
from core.services.ai.investigation.compose_descriptions import PLACEHOLDER
from core.services.ai.investigation.compose_sections import dedupe_headings, units
from core.views.ai_chat.chat_pipeline.investigate import ensure_document

from .support import make_user
from .test_compose_guide import ASK, GuideProvider, Result

ENGLISH = ("This guide explains the screens. Open Plans to see the status of your trial and Documentation for the manual. "
           "Select the account, enter the amount and the date, then save the transaction. ") * 40


def _guide(title: str, tabs: int = 5) -> str:
    return f"# {title}\n\nIntro.\n" + "\n".join(f"## Chapter {n}\n### Part {n}\nText." for n in range(tabs))


class DescriptionsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("ground_admin", sysadmin=True)

    def test_no_documented_page_is_a_placeholder(self):
        data = json.loads((Path(settings.BASE_DIR) / "doc_engine" / "content" / "page_descriptions.json").read_text(encoding="utf-8"))
        self.assertEqual([k for k, v in data.items() if str(v.get("purpose", "")).startswith(PLACEHOLDER)], [])

    def test_every_tab_and_dialog_carries_its_documented_text(self):
        import re

        for unit in units(self.admin):
            evidence = json.loads(unit["evidence"])
            for tab in evidence.get("tabs", []):
                self.assertTrue(tab.get("description"), f"{unit['page']} > {tab['name']} has no description")
                for dialog in tab.get("dialogs", []):
                    self.assertTrue(isinstance(dialog, dict) and dialog.get("purpose"), f"{unit['page']} > {tab['name']} > {dialog}")
        for text in (u["evidence"] for u in units(self.admin)):
            self.assertIsNone(re.search(r"industry|contact details", text))   # the company form has neither (it has payroll fields)

    def test_company_dialog_lists_the_real_form_fields(self):
        text = next(u["evidence"] for u in units(self.admin) if u["page"] == "Settings" and "Companies" in u["tabs"])
        for field in ("Display Name", "Group Name", "Payment Day", "Default Bank", "Per Diem Amount"):
            self.assertIn(field, text)

    def test_a_screen_split_in_parts_is_one_chapter(self):
        plan = [u for u in units(self.admin) if u["page"] == "Financial Advisor"]
        self.assertEqual(len(plan), 3)
        self.assertEqual([u["heading"] for u in plan], ["Financial Advisor", "", ""])
        self.assertNotIn("Open it from the menu", plan[1]["fallback"])
        self.assertNotIn("(2/3)", plan[1]["fallback"])

    def test_the_fallback_is_the_documented_text_not_a_filler_line(self):
        text = next(u["fallback"] for u in units(self.admin) if u["page"] == "Financial Advisor")
        self.assertIn("comparing income against expenses", text)            # Cash Flow's documented purpose
        self.assertNotIn("Review the records on this tab", text)

    def test_getting_started_comes_first_and_employment_has_its_salary_dialogs(self):
        plan = units(self.admin)
        self.assertEqual(plan[0]["page"], "Signing up and signing in")
        self.assertIn("Forgot Password", plan[0]["evidence"])
        employment = next(u["evidence"] for u in plan if u["page"] == "Employment")
        self.assertIn("Add Salary Entry", employment)
        self.assertIn("per diem", employment.lower())

    def test_the_instructions_forbid_invention_source_talk_and_repeated_generate_file(self):
        self.assertIn("ONCE", DEFAULT_INSTRUCTIONS)
        self.assertIn("Never invent", DEFAULT_DOCUMENT_INSTRUCTIONS)
        self.assertIn("provided documentation", DEFAULT_DOCUMENT_INSTRUCTIONS)
        self.assertIn("same heading twice", DEFAULT_DOCUMENT_INSTRUCTIONS)


class HeadingsTest(SimpleTestCase):
    def test_a_repeated_heading_is_dropped_but_a_repeat_after_text_is_kept(self):
        text = "### Overview\n### Overview\nBody\n### Cash Flow\n\n### cash flow\nBody\n### Overview\nMore"
        out = dedupe_headings(text)
        self.assertEqual(out.count("### Overview"), 2)
        self.assertEqual(out.lower().count("### cash flow"), 1)


class LanguageTest(TestCase):
    def test_a_long_english_guide_is_english(self):
        self.assertEqual(document_language(ENGLISH), "en")

    def test_arabic_french_and_german_documents_keep_their_language(self):
        self.assertEqual(document_language("هذا دليل المستخدم لتطبيق ويلث فلو. " * 20), "ar")
        self.assertEqual(document_language("Ce guide explique les écrans de votre compte et les soldes. Ouvrez le menu pour voir vos dépenses. " * 10), "fr")
        self.assertEqual(document_language("Diese Anleitung erklärt die Bildschirme Ihres Kontos und die Salden. Öffnen Sie das Menü für Ihre Ausgaben. " * 10), "de")

    def test_the_export_of_an_english_guide_has_an_english_date_line(self):
        from core.models import AIConversation, AIMessage
        from core.services.ai.exports.build import document_for

        conv = AIConversation.objects.create(user=make_user("lang_user"))
        AIMessage.objects.create(conversation=conv, role="user", content="write the user guide as a Word document")
        reply = AIMessage.objects.create(conversation=conv, role="assistant", content=_guide("WealthFlow User Guide") + ENGLISH)
        doc = document_for(reply)
        self.assertEqual(doc.lang, "en")
        self.assertTrue(doc.generated.startswith("Generated on"))


class DraftsTest(TestCase):
    def calls(self, *texts):
        return [{"tool": "generate_file", "status": "success", "arguments": {"format": "docx", "content": t}} for t in texts]

    def test_three_drafts_of_one_guide_become_one(self):
        drafts = [_guide("دليل المستخدم — WealthFlow", 4), _guide("دليل المستخدم - WealthFlow", 6), _guide("دليل المستخدم – WealthFlow", 5)]
        self.assertEqual(superseded_drafts(self.calls(*drafts)), {0, 2})        # the longest (index 1) is kept
        text, _ = from_tool_calls(SimpleNamespace(tool_calls=self.calls(*drafts)), None)
        self.assertEqual(text.count("# دليل المستخدم"), 1)
        self.assertEqual(text.count("## Chapter 0"), 1)

    def test_drafts_with_different_titles_but_the_same_chapters_are_still_one_document(self):
        a = "# Guide A\n## One\n## Two\n## Three\n## Four\ntext"
        b = "# Another title\n## One\n## Two\n## Three\n## Four\n## Five\ntext more"
        self.assertEqual(superseded_drafts(self.calls(a, b)), {0})

    def test_parts_about_different_things_are_all_kept(self):
        a = "# Part one\n## Sales\n## Costs\n## Taxes\ntext"
        b = "# Part two\n## Staff\n## Offices\n## Cars\ntext"
        self.assertEqual(superseded_drafts(self.calls(a, b)), set())
        text, _ = from_tool_calls(SimpleNamespace(tool_calls=self.calls(a, b)), None)
        self.assertIn("## Sales", text)
        self.assertIn("## Staff", text)

    def test_short_texts_and_code_are_never_dropped(self):
        self.assertEqual(superseded_drafts(self.calls("print(1)", "print(1)")), set())


class AgentGuideTest(TestCase):
    """Agent mode: the model wrote files with generate_file; a guide to the app is still written by the app."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("agent_guide_admin", sysadmin=True)

    def agent_result(self):
        res = Result()
        res.content = "The guide is ready."
        res.steps = [{"tool": "generate_file", "status": "success", "arguments": {"format": "docx", "title": "Guide", "content": _guide("Own draft", 5)}},
                     {"tool": "generate_file", "status": "success", "arguments": {"format": "docx", "content": _guide("Own draft", 6)}}]
        return res

    def test_the_app_writes_the_guide_and_the_models_drafts_leave_the_file(self):
        prov = GuideProvider()
        prov.user = self.admin
        res = self.agent_result()
        self.assertTrue(ensure_document(prov, ASK, res, 24000, self.admin, None))
        self.assertTrue(res.content.startswith("# WealthFlow user guide"))
        self.assertEqual(res.content.count("# WealthFlow user guide"), 1)
        self.assertNotIn("Own draft", res.content)
        self.assertTrue(all("content" not in s["arguments"] for s in res.steps))
        self.assertTrue(all(s["status"] == "success" for s in res.steps))     # the file formats the model chose are kept

    def test_a_report_on_the_users_own_data_is_left_to_the_model(self):
        prov = GuideProvider(about_app="NO")
        prov.user = self.admin
        res = self.agent_result()
        self.assertFalse(ensure_document(prov, "write a word report of my expenses", res, 24000, self.admin, None))
        self.assertEqual(res.content, "The guide is ready.")
        self.assertTrue(all("content" in s["arguments"] for s in res.steps))

    def test_drop_model_drafts_keeps_datasets_and_tables(self):
        steps = [{"tool": "generate_file", "arguments": {"content": "x", "dataset": {"model": "Expense"}, "table": {"columns": []}}},
                 {"tool": "app_routes", "arguments": {"content": "keep"}}]
        drop_model_drafts(steps)
        self.assertEqual(steps[0]["arguments"], {"dataset": {"model": "Expense"}, "table": {"columns": []}})
        self.assertEqual(steps[1]["arguments"], {"content": "keep"})
