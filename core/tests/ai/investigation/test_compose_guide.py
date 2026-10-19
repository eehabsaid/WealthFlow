"""The user guide is written section by section from the LIVE app (every screen, every Settings tab), never cut off by the
model's context window, and a section the model cannot write is filled from the app's own screen list."""

from __future__ import annotations

import re

from django.test import TestCase

from core.models import AppSettings
from core.services.ai.app_pages import app_pages
from core.services.ai.investigation.compose_sections import units
from core.views.ai_chat.chat_pipeline.investigate import ensure_document

from .support import make_user

ASK = "can you generate a word document for the app business as user guide?"


class GuideProvider:
    """Answers the three kinds of prompt the guide writer sends; records every call."""

    supports_tools = False
    user = None

    def __init__(self, about_app="YES", fail_sections=False, drop_last_tab=False):
        self.calls, self.about_app, self.fail_sections, self.drop_last_tab = [], about_app, fail_sections, drop_last_tab

    def generate(self, messages, tools=None, **kwargs):
        system, ask = messages[0]["content"], messages[-1]["content"]
        self.calls.append({"system": system, "ask": ask})
        if "exactly one word" in system:
            return {"content": self.about_app}
        if "Write ONLY the document title" in ask:
            return {"content": "# WealthFlow user guide\n\nThis guide explains every screen of the app step by step."}
        if "Write ONLY this sub-section" in ask:
            name = ask.split('starting with the line "### ', 1)[1].split('"', 1)[0]
            return {"content": f"### {name}\n\n" + "Open this tab and follow the steps shown on screen. " * 4}
        if "Write ONLY this section" in ask:
            if self.fail_sections:
                return {"error": "model unavailable"}
            title = ask.split('Write ONLY this section: "', 1)[1].split('"', 1)[0]
            body = "Open the screen from the menu and use its tabs to manage your records. " * 3
            part = re.search(r"part (\d+) of \d+", ask)
            names = [unit["tabs"] for unit in units(self.user) if unit["title"] == title and unit["part"][0] == int(part.group(1) if part else 1)][0]
            tabs = names[:-1] if self.drop_last_tab and len(names) > 1 else names
            return {"content": f"\n\n## {title}\n\n{body}\n\n" + "\n\n".join(f"## {n}\n\n{body}" for n in tabs)}
        return {"content": "x" * 600}


class Result:
    def __init__(self):
        self.content, self.steps, self.results, self.reason, self.llm_calls = "Let me compose it.", [], [], "answered", 0


def tab_names(user):
    return [t["name"] for p in app_pages() if user_ok(user, p) for t in (p.get("tabs") or [])]


def user_ok(user, page):
    from core.authentication.utils.auth_utils import user_is_sysadmin

    return user_is_sysadmin(user) or not page.get("admin_only")


class GuideTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("guide_admin", sysadmin=True)
        cls.member = make_user("guide_member")

    def run_guide(self, user, provider):
        res = Result()
        provider.user = user
        self.assertTrue(ensure_document(provider, ASK, res, 24000, user, None))
        return res.content

    def test_every_screen_and_every_settings_tab_is_in_the_guide_one_model_call_per_section(self):
        prov = GuideProvider()
        doc = self.run_guide(self.admin, prov)
        plan = units(self.admin)
        self.assertGreater(len(plan), 17)                                  # Settings is split into several parts
        for unit in plan:
            if unit["heading"]:                                            # a screen split in parts is ONE chapter
                self.assertIn(f"## {unit['heading']}", doc)
        for name in tab_names(self.admin):
            self.assertIn(name, "\n".join(u["evidence"] for u in plan))   # every tab reaches a section call
        self.assertTrue(doc.startswith("# WealthFlow user guide"))
        self.assertEqual(len(prov.calls), 3 + len(plan))                   # "is it about the app", "which language", the intro, one per section
        self.assertNotIn("Settings (1/", doc)                             # parts of one screen are one chapter, no "(1/4)" labels
        self.assertEqual(doc.count("## Settings\n"), 1)

    def test_each_section_call_only_carries_its_own_tabs(self):
        prov = GuideProvider()
        self.run_guide(self.admin, prov)
        parts = [c for c in prov.calls if 'Write ONLY this section: "Settings"' in c["ask"]]
        first, last = next(c for c in parts if "part 1 of" in c["ask"]), next(c for c in parts if "part 4 of" in c["ask"])
        self.assertNotEqual(first["ask"].split("SCREEN:")[1], last["ask"].split("SCREEN:")[1])
        self.assertLess(len(first["ask"]), 24000)                          # fits a small local context window

    def test_a_member_never_gets_the_admin_only_screens(self):
        doc = self.run_guide(self.member, GuideProvider())
        self.assertNotIn("Settings", doc)
        self.assertIn("## Balance", doc)

    def test_sections_the_model_cannot_write_are_filled_from_the_app_itself(self):
        doc = self.run_guide(self.admin, GuideProvider(fail_sections=True))
        for unit in units(self.admin):
            if unit["heading"]:                                            # a screen split in parts is ONE chapter
                self.assertIn(f"## {unit['heading']}", doc)
        for name in tab_names(self.admin):
            self.assertIn(f"### {name}", doc)

    def test_when_time_runs_out_the_rest_is_still_covered(self):
        import core.services.ai.investigation.compose as compose

        real = compose.time.monotonic
        ticks = iter(range(0, 10**9, 10**5))                              # every clock read jumps a day: the budget is gone at once
        compose.time.monotonic = lambda: next(ticks)
        try:
            prov = GuideProvider()
            doc = self.run_guide(self.admin, prov)
        finally:
            compose.time.monotonic = real
        for unit in units(self.admin):
            if unit["heading"]:                                            # a screen split in parts is ONE chapter
                self.assertIn(f"## {unit['heading']}", doc)
        self.assertFalse([c for c in prov.calls if "Write ONLY this section" in c["ask"]])   # no model time left: all from the app itself

    def test_the_editable_instructions_are_what_the_model_is_told(self):
        AppSettings.set("ai_document_instructions", "CUSTOM RULE: write in short bullet points.", user=None)
        prov = GuideProvider()
        self.run_guide(self.member, prov)
        sections = [c for c in prov.calls if "Write ONLY this section" in c["ask"]]
        self.assertTrue(sections and all(c["system"] == "CUSTOM RULE: write in short bullet points." for c in sections))

    def test_a_report_on_the_users_own_data_is_one_call_from_the_tool_evidence(self):
        prov = GuideProvider(about_app="NO")
        res = Result()
        res.results = [("app_data_query", {"model": "Expense"}, "total 100.00")]
        self.assertTrue(ensure_document(prov, "write a report of my expenses as a word document", res, 24000, self.member, None))
        self.assertEqual(len(prov.calls), 2)
        self.assertIn("total 100.00", prov.calls[1]["ask"])


class GuideCoverageTest(TestCase):
    """The reported bug: the section for Settings tabs 16-20 only contained "Legal Text" and silently dropped four tabs."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("cover_admin", sysadmin=True)

    def run_guide(self, prov):
        prov.user = self.admin
        res = Result()
        self.assertTrue(ensure_document(prov, ASK, res, 24000, self.admin, None))
        return res.content, prov

    def test_a_tab_the_model_skipped_is_written_on_its_own_so_nothing_is_missing(self):
        doc, prov = self.run_guide(GuideProvider(drop_last_tab=True))
        for name in tab_names(self.admin):
            self.assertIn(f"### {name}", doc, name)
        singles = [c for c in prov.calls if "Write ONLY this sub-section" in c["ask"]]
        self.assertTrue(singles)
        self.assertTrue(all(len(c["ask"]) < 5000 for c in singles))     # one tab per call: small prompt

    def test_a_skipped_tab_the_model_cannot_write_comes_from_the_apps_own_tab_list(self):
        class Flaky(GuideProvider):
            def generate(self, messages, tools=None, **kwargs):
                if "Write ONLY this sub-section" in messages[-1]["content"]:
                    return {"error": "unavailable"}
                return super().generate(messages, tools, **kwargs)

        doc, _ = self.run_guide(Flaky(drop_last_tab=True))
        for name in tab_names(self.admin):
            self.assertIn(f"### {name}", doc, name)

    def test_one_title_per_section_and_the_models_own_headings_sit_below_it(self):
        doc, _ = self.run_guide(GuideProvider())
        h2 = [line[3:] for line in doc.splitlines() if line.startswith("## ")]
        self.assertEqual(len(h2), len(set(h2)))                          # no "Settings / Settings"
        self.assertEqual(set(h2), {u["heading"] for u in units(self.admin) if u["heading"]})

    def test_a_section_cut_off_by_the_output_limit_has_its_half_written_tab_rewritten_alone(self):
        class CutOff(GuideProvider):
            def generate(self, messages, tools=None, **kwargs):
                res = super().generate(messages, tools, **kwargs)
                if "Write ONLY this section" in messages[-1]["content"]:
                    res["completion_tokens"] = kwargs["max_tokens"]          # the model stopped at the limit
                return res

        doc, prov = self.run_guide(CutOff())
        for name in tab_names(self.admin):
            self.assertIn(name, doc)
        self.assertTrue([c for c in prov.calls if "Write ONLY this sub-section" in c["ask"]])
