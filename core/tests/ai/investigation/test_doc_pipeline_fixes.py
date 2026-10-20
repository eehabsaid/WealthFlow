"""Scripted reproductions of the user-guide failure (classifier NO + only app_data_models), the native tool protocol, empty
replies, the reasoning setting, translated-guide duplicates, the title and contents lists."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from core.integrations.ai_provider.ollama_payload import apply_runtime_flags, native_messages, resolve_think
from core.models import AppSettings
from core.services.ai.investigation import loop as inv
from core.services.ai.investigation.compose_align import align_to_source
from core.services.ai.investigation.compose_contents import drop_contents
from core.services.ai.investigation.compose_quality import report, sanitize
from core.services.ai.investigation.compose_sections import units
from core.services.ai.investigation.compose_title import guide_title, with_app_name
from core.services.ai.investigation.doc_path import choose_path
from core.services.ai.investigation.nudges import investigate_nudge
from core.views.ai_chat.chat_pipeline.investigate import ensure_document

from .support import ScriptedProvider, make_user, tool_call
from .test_compose_guide import ASK, GuideProvider, Result, user_ok


def out(results=(), steps=()):
    return SimpleNamespace(results=list(results), steps=list(steps))


class StructuralPathTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("path_admin", sysadmin=True)

    def test_log_reproduction_classifier_no_and_only_a_table_list_runs_the_guide(self):
        prov, res = GuideProvider(about_app="NO"), Result()
        prov.user = self.admin
        res.results = [("app_data_models", {}, '{"models":["Expense","Bank"]}')]
        with self.assertLogs("core.ai.pipeline", "WARNING") as logs:
            self.assertTrue(ensure_document(prov, ASK, res, 24000, self.admin, None))
        plan = units(self.admin)
        for unit in plan:
            if unit["heading"]:
                self.assertIn(f"## {unit['heading']}", res.content)
        self.assertEqual(len([c for c in prov.calls if "Write ONLY this section" in c["ask"]]), len(plan))   # one section per screen / tab group
        line = next(m for m in logs.output if "[AI-DOC]" in m)
        self.assertIn("path=guide reason=no_user_rows_in_evidence classifier=NO evidence_tools=['app_data_models']", line)

    def test_decision_table(self):
        rows = out([("app_data_query", {}, '{"rows":[1]}')])
        self.assertEqual(choose_path(rows, False)[0], "single")
        self.assertEqual(choose_path(out([("app_computed_figures", {}, "{}")]), False)[0], "single")
        self.assertEqual(choose_path(out(), False)[0], "guide")
        self.assertEqual(choose_path(out([("app_data_models", {}, "{}")]), False)[0], "guide")
        self.assertEqual(choose_path(out([("app_data_query", {}, '{"error":"x"}')]), False)[0], "guide")   # a failed query is not evidence
        self.assertEqual(choose_path(rows, True)[0], "guide")                                          # the classifier is an extra signal
        dataset = out(steps=[{"tool": "generate_file", "status": "success", "arguments": {"dataset": {"model": "Expense"}}}])
        self.assertEqual(choose_path(dataset, False)[0], "single")
        self.assertEqual(choose_path(out(), False, own_file=True)[0], "single")                        # the model's own file, nothing to judge it by

    def test_real_rows_still_get_a_report_in_one_call(self):
        prov = ScriptedProvider([{"content": "NO"}, {"content": "Report text. " * 60}])
        res = Result()
        res.results = [("app_data_query", {}, '{"rows":[{"amount":5}]}')]
        self.assertTrue(ensure_document(prov, "write my expenses report as a word document", res, 24000, self.admin, None))
        self.assertEqual(len(prov.calls), 2)


class NativeProtocolTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user("native_user")

    def test_native_messages_for_a_provider_that_accepts_them(self):
        prov = ScriptedProvider([tool_call("app_data_models"), {"content": "Tables listed."}])
        prov.native_tool_messages = True
        inv.investigate(prov, self.user, "what tables exist?")
        msgs = prov.calls[1]["messages"]
        call = next(m for m in msgs if m.get("tool_calls"))
        self.assertEqual((call["role"], call["tool_calls"][0]["function"]["name"], isinstance(call["tool_calls"][0]["function"]["arguments"], dict)),
                         ("assistant", "app_data_models", True))
        result = next(m for m in msgs if m["role"] == "tool")
        self.assertEqual(result["tool_name"], "app_data_models")
        self.assertFalse(any(str(m["content"]).startswith("TOOL RESULT") for m in msgs))

    def test_text_protocol_stays_for_other_providers(self):
        prov = ScriptedProvider([tool_call("app_data_models"), {"content": "Tables listed."}])   # native tools, but no native messages
        inv.investigate(prov, self.user, "what tables exist?")
        msgs = prov.calls[1]["messages"]
        self.assertTrue(any(m["role"] == "assistant" and m["content"].startswith("Calling app_data_models") for m in msgs))
        self.assertTrue(any(m["role"] == "system" and m["content"].startswith("TOOL RESULT (app_data_models") for m in msgs))
        self.assertFalse(any(m["role"] == "tool" for m in msgs))

    def test_ollama_gets_arguments_as_objects(self):
        msgs = native_messages([{"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "x", "arguments": '{"a": 1}'}}]}])
        self.assertEqual(msgs[0]["tool_calls"][0]["function"]["arguments"], {"a": 1})


class EmptyReplyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user("empty_user")

    def run_loop(self, script, **kw):
        prov = ScriptedProvider(script)
        return inv.investigate(prov, self.user, "write the user guide", **kw), prov

    def test_empty_after_a_tool_result_is_retried_once_then_nudged_without_a_tool_name(self):
        res, prov = self.run_loop([tool_call("app_data_models")] + [{"content": ""}] * 3 + [{"content": "The guide covers the screens."}],
                                  write_tokens=4096)
        self.assertEqual(res.nudges, 1)
        self.assertEqual(prov.calls[2]["messages"], prov.calls[1]["messages"])           # the retry sends the same messages
        nudge = prov.calls[4]["messages"][-1]["content"]
        self.assertIn("DO have full read access", nudge)
        self.assertNotIn("app_data_models", nudge)                                        # no hard-coded favourite
        self.assertIn("app_routes", nudge)
        self.assertIn("app_knowledge_search", nudge)

    def test_nudge_names_only_offered_tools(self):
        self.assertNotIn("app_routes", investigate_nudge({"app_data_models", "app_data_query"}, document=True))
        self.assertEqual(investigate_nudge(set()).count("("), 0)
        self.assertIn("app_data_query", investigate_nudge({"app_data_models", "app_data_query"}))


class ThinkSettingTest(SimpleTestCase):
    def test_auto_follows_the_caller(self):
        self.assertTrue(resolve_think("auto", "on"))
        self.assertFalse(resolve_think("auto", "off"))
        self.assertFalse(resolve_think("auto", None))
        self.assertTrue(resolve_think("on", "off"))
        self.assertFalse(resolve_think("off", "on"))

    def test_payload_flag(self):
        self.assertIs(apply_runtime_flags({}, "qwen3:8b", "", "auto", "on")["think"], True)
        self.assertIs(apply_runtime_flags({}, "qwen3:8b", "", "auto", "off")["think"], False)
        self.assertNotIn("think", apply_runtime_flags({}, "llama3.1:8b", "", "on", "on"))


class ThinkReachesTheProviderTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("think_admin", sysadmin=True)

    def test_classifier_off_and_document_writing_on(self):
        prov = GuideProvider()
        prov.user = self.admin
        seen = []
        original = prov.generate
        prov.generate = lambda messages, tools=None, **kw: (seen.append((messages[0]["content"][:30], kw.get("reasoning"))), original(messages, tools, **kw))[1]
        ensure_document(prov, ASK, Result(), 24000, self.admin, None)
        self.assertEqual(seen[0][1], "off")                      # "Answer with exactly one word": the classifier
        self.assertTrue(all(r == "on" for _, r in seen[2:]))      # intro and sections

    def test_setting_validation_and_default(self):
        from core.services.ai.agent.settings import get_agent_settings, validate_agent_settings

        cur = get_agent_settings()
        self.assertEqual(cur["ai_think"], "auto")
        self.assertIsNotNone(validate_agent_settings({"ai_think": "on"}, cur)[0])
        self.assertIsNotNone(validate_agent_settings({"ai_think": "maybe"}, cur)[1])


SOURCE = "# WealthFlow user guide\n\nIntro.\n\n## Balance\n\n### Banks\n\nbank text one two three four\n\n### Currencies\n\ncurrency text five six\n\n## Expenses\n\n### List\n\nlist text seven eight\n"


class TranslatedGuideTest(SimpleTestCase):
    def test_a_repeated_chapter_and_sub_heading_are_removed_by_position(self):
        ar = ("# دليل WealthFlow\n\nمقدمة.\n\n## الرصيد\n\n### البنوك\n\nنص البنك واحد اثنان\n\n### البنوك\n\nنص البنك واحد اثنان ثلاثة\n\n### العملات\n\nنص العملات\n\n"
              "## الرصيد\n\n### البنوك\n\nنص البنك واحد اثنان\n\n## المصروفات\n\n### القائمة\n\nنص القائمة\n")
        out_text = sanitize(ar, english=False, source=SOURCE)
        found = report(out_text)
        self.assertEqual((found["chapters"], found["repeated_chapters"], found["repeated_sub_headings"]), (2, 0, 0))
        self.assertEqual(out_text.count("### العملات"), 1)

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
