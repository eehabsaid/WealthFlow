"""Agent tools: screens/routes, UI text, verified figures (everyone) and callers / git / feature trace (sysadmin only)."""

from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase

from core.services.ai.investigation import app_tools, code_extra
from core.services.ai.investigation.defs import CODE_TOOLS, investigation_tool_schemas
from core.services.ai.tools import validate_and_execute_tool
from core.tests.ai.investigation.support import make_user, seed_tenant

NEW_CODE_TOOLS = {"app_callers", "app_git_history", "app_trace_feature"}
NEW_OPEN_TOOLS = {"app_computed_figures", "app_routes", "app_i18n_search"}


def names(user):
    return {s["function"]["name"] for s in investigation_tool_schemas(user)}


class ToolVisibilityTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.member, cls.admin = make_user("tv_member"), make_user("tv_admin", sysadmin=True)

    def test_members_get_the_open_tools_but_no_code_tools(self):
        got = names(self.member)
        self.assertTrue(NEW_OPEN_TOOLS <= got)
        self.assertFalse(got & set(CODE_TOOLS))

    def test_sysadmin_gets_every_new_tool(self):
        self.assertTrue((NEW_OPEN_TOOLS | NEW_CODE_TOOLS) <= names(self.admin))

    def test_a_member_cannot_run_a_code_tool_even_by_name(self):
        for tool, args in (("app_callers", {"symbol": "ExpenseService"}), ("app_git_history", {"path": "manage.py"}),
                           ("app_trace_feature", {"feature": "expenses"})):
            _audit, res = validate_and_execute_tool(tool, args, self.member)
            self.assertIn("limited to the system administrator", str(res["data"]["error"]), tool)


class OpenToolsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.member, cls.admin = make_user("ot_member"), make_user("ot_admin", sysadmin=True)
        seed_tenant(cls.member, "M", expenses=3, amount="40.00")

    def test_routes_lists_screens_filters_and_hides_admin_pages_and_django_routes_from_members(self):
        all_screens = app_tools.routes(self.member, {})
        self.assertGreater(all_screens["total"], 5)
        self.assertNotIn("django_routes", all_screens)
        self.assertFalse(any(s.get("admin_only") for s in all_screens["screens"]))
        gold = app_tools.routes(self.member, {"query": "gold"})
        self.assertTrue(gold["screens"])
        self.assertTrue(all("gold" in str(s).lower() for s in gold["screens"]))
        self.assertIn("no screen matched", app_tools.routes(self.member, {"query": "zzzqqq"})["note"])

    def test_sysadmin_also_gets_the_django_routes(self):
        out = app_tools.routes(self.admin, {})
        self.assertIn("django_routes", out)
        self.assertTrue(out["django_routes"])

    def test_i18n_search_finds_ui_text_in_each_language_and_validates_input(self):
        en = app_tools.i18n_search(self.member, {"term": "exchange rate"})
        self.assertTrue(en["matches"])
        self.assertIn("key", en["matches"][0])
        self.assertTrue(app_tools.i18n_search(self.member, {"term": "nav_", "lang": "ar"})["matches"])
        self.assertIn("error", app_tools.i18n_search(self.member, {"term": "x"}))
        self.assertIn("lang must be", app_tools.i18n_search(self.member, {"term": "gold", "lang": "xx"})["error"])
        self.assertIn("note", app_tools.i18n_search(self.member, {"term": "qqzzxxww"}))

    def test_computed_figures_uses_the_instant_answer_engine_for_the_users_own_rows(self):
        out = app_tools.computed_figures(self.member, {"question": "show my expenses for September 2026"})
        self.assertIn("VERIFIED DATA", out["figures"])
        self.assertIn("120.00 EGP across 3 transactions", out["figures"])
        other = make_user("ot_other")
        self.assertNotIn("120.00", str(app_tools.computed_figures(other, {"question": "show my expenses for September 2026"})))

    def test_computed_figures_says_so_when_nothing_is_computable(self):
        out = app_tools.computed_figures(self.member, {"question": "tell me a joke about camels"})
        self.assertIsNone(out["figures"])
        self.assertIn("app_data_query", out["note"])
        self.assertIn("error", app_tools.computed_figures(self.member, {"question": " "}))


class CodeExtraToolsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("ce_admin", sysadmin=True)

    def test_callers_finds_usages_but_not_the_definition(self):
        out = code_extra.callers(self.admin, {"symbol": "code_access_allowed"})
        self.assertTrue(out["usages"])
        self.assertTrue(all(not m["text"].lstrip().startswith("def ") for m in out["usages"]))
        self.assertTrue(any("investigation" in f for f in out["files"]))
        self.assertIn("error", code_extra.callers(self.admin, {"symbol": "not a name!"}))
        self.assertIn("note", code_extra.callers(self.admin, {"symbol": "zzNever" + "UsedAnywhere9"}))

    def test_trace_feature_reports_every_layer_with_file_and_line(self):
        out = code_extra.trace_feature(self.admin, {"feature": "exchange rates"})
        for layer in ("frontend", "urls", "views", "models"):
            self.assertIn(layer, out)
        self.assertTrue(out["frontend"]["hits"] or out["views"]["hits"] or out["models"]["hits"])
        first = next(h for layer in ("frontend", "views", "models", "urls") for h in out[layer]["hits"])
        self.assertTrue({"file", "line", "text"} <= set(first))
        self.assertIn("error", code_extra.trace_feature(self.admin, {"feature": "ab"}))

    def test_secrets_are_still_redacted_in_trace_hits(self):
        out = code_extra.trace_feature(self.admin, {"feature": "SECRET_KEY"})
        self.assertNotIn("django-insecure", str(out))

    def test_git_history_log_and_blame_use_a_fixed_git_command_without_a_shell(self):
        class Done:
            returncode, stdout = 0, "abc1234|2026-10-01|Ehab|fix: thing\ndef5678|2026-09-30|Ehab|feat: other\n"

        with patch.object(code_extra.subprocess, "run", return_value=Done()) as run:
            out = code_extra.git_history(self.admin, {"path": "manage.py", "limit": 2})
        self.assertEqual(out["commits"][0], {"commit": "abc1234", "date": "2026-10-01", "author": "Ehab", "subject": "fix: thing"})
        args, kwargs = run.call_args
        self.assertEqual(args[0][:2], ["git", "log"])
        self.assertNotIn("shell", kwargs)
        self.assertEqual(args[0][-2:], ["--", "manage.py"])

        class Blame:
            returncode, stdout = 0, "abc1234 (Ehab 2026-10-01 1) import os\n"

        with patch.object(code_extra.subprocess, "run", return_value=Blame()) as run:
            out = code_extra.git_history(self.admin, {"path": "manage.py", "action": "blame", "start_line": 1, "end_line": 500})
        self.assertIn("import os", out["blame"][0])
        self.assertIn("1,80", run.call_args[0][0])        # the blame range is capped at 80 lines

    def test_git_history_degrades_gracefully_without_git_and_rejects_bad_paths(self):
        with patch.object(code_extra.subprocess, "run", side_effect=FileNotFoundError):
            self.assertIn("not available", code_extra.git_history(self.admin, {"path": "manage.py"})["error"])
        self.assertIn("error", code_extra.git_history(self.admin, {"path": "../etc/passwd"}))
        self.assertIn("error", code_extra.git_history(self.admin, {"path": ".env"}))
        self.assertIn("must be a file", code_extra.git_history(self.admin, {"path": "core"})["error"])
