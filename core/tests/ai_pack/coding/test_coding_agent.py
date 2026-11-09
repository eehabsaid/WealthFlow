"""Coding-agent foundation: index, context picker, plan check, protected files, verification wording, memory, and the sysadmin-only tools."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.authentication.services import AuthWorkflowService
from ai.services.coding import context, index, memory, tools, verify
from ai.services.coding.config import protected_reason, test_module
from ai.services.coding.plan import plan_check
from ai.services.tools.defs import AI_TOOL_REGISTRY
from ai.services.investigation.defs import CODE_TOOLS, investigation_tool_schemas

User = get_user_model()


class IndexTests(TestCase):
    def test_finds_classes_models_and_files(self):
        hit = index.find("ExpenseService")[0]
        self.assertEqual(hit["file"], "core/services/expenses/expense_service.py")
        self.assertIn("Expense", {m for h in index.find("Expense") for m in h["models"]})

    def test_callers_lists_importers_but_not_unrelated_files(self):
        callers = index.callers("ExpenseService")
        self.assertIn("core/views/expense_views.py", callers)
        self.assertNotIn("core/models/salary.py", callers)

    def test_routes_are_indexed_and_dependencies_read(self):
        self.assertIn("api/financial-advisor/ai/chat/", index.get()["files"]["ai/urls_chat.py"]["routes"])
        self.assertIn("Django", index.get()["dependencies"]["python"])

    def test_index_rebuilds_when_a_file_changes(self):
        first = index.get()
        self.assertIs(index.get(), first)


class SafetyAndPlanTests(TestCase):
    def test_financial_and_tenancy_files_are_protected(self):
        for path in ("core/services/financial_advisor/cash_flow_forecast_service/custom_projection.py", "core/services/shared/base_currency.py",
                     "core/validators/ownership.py", "db.sqlite3", "core/migrations/0001_initial.py"):
            self.assertTrue(protected_reason(path), path)
        self.assertEqual(protected_reason("ai/static/ai/js/ai_shell.js"), "")

    def test_plan_flags_protected_over_limit_and_maps_tests(self):
        plan = plan_check(["core/services/expenses/expense_service.py", "ai/static/ai/js/ai_shell.js", "core/new_file.py"])
        by = {r["file"]: r for r in plan["files"]}
        self.assertTrue(by["core/services/expenses/expense_service.py"]["protected"])
        self.assertIn("core/services/expenses/expense_service.py", plan["needs_owner_approval"])
        self.assertFalse(by["core/new_file.py"]["exists"])
        self.assertIn("core.tests.expenses", plan["tests_to_run"])

    def test_test_module_uses_the_longest_folder_prefix(self):
        self.assertEqual(test_module("core/services/shared/base_currency.py"), "core.tests.currency")
        self.assertEqual(test_module("ai/services/actions/expense.py"), "ai.tests")
        self.assertEqual(test_module("README.md"), "")


class ContextTests(TestCase):
    def test_picks_the_relevant_skill_within_the_budget(self):
        picked = context.pick("record a new expense and update the balance", 2500)
        self.assertIn("expenses", [s["name"] for s in picked["skills"]])
        self.assertLessEqual(picked["used_chars"], 2500)

    def test_nothing_relevant_returns_nothing_instead_of_noise(self):
        self.assertEqual(context.pick("zzzz qqqq xxxx", 3000)["skills"], [])


class MemoryTests(TestCase):
    def test_add_dedupes_and_refuses_secrets(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(memory, "FILE", Path(tmp) / "MEMORY.md"):
            self.assertIn("lesson one", memory.add("lesson one"))
            self.assertEqual(memory.add("lesson one"), "already recorded")
            self.assertEqual(len(memory.entries()), 1)
            with self.assertRaises(memory.MemoryError_):
                memory.add("the api_key is abc")
            with self.assertRaises(memory.MemoryError_):
                memory.add("   ")


class VerifyWordingTests(TestCase):
    def steps(self, *statuses):
        return [{"step": f"s{i}", "status": s, "detail": ""} for i, s in enumerate(statuses)]

    def run_verify(self, results):
        with patch.object(verify, "_run", side_effect=results), patch.object(verify, "i18n_parity", return_value={"step": "i18n", "status": "PASSED", "detail": ""}):
            return verify.verify(["README.md"])

    def ok(self, name):
        return {"step": name, "status": "PASSED", "detail": ""}

    def test_all_passed_still_says_browser_e2e_not_run(self):
        res = self.run_verify([self.ok("a"), self.ok("b"), self.ok("c")])
        self.assertTrue(res["overall"].startswith("VERIFIED"))
        self.assertIn("browser E2E not run", res["overall"])
        self.assertEqual([s["status"] for s in res["steps"] if "E2E" in s["step"]], ["NOT RUN"])

    def test_one_failure_means_not_verified(self):
        res = self.run_verify([self.ok("a"), {"step": "tests", "status": "FAILED", "detail": "x"}, self.ok("c")])
        self.assertTrue(res["overall"].startswith("NOT VERIFIED"))
        self.assertIn("tests", res["overall"])

    def test_i18n_parity_passes_on_the_repo(self):
        self.assertEqual(verify.i18n_parity()["status"], "PASSED")

    def test_line_limit_flags_a_long_file(self):
        self.assertEqual(verify.line_limits(["db.sqlite3"])["status"], "PASSED")
        with patch.dict(verify.load.__globals__["_DEFAULT"], {"max_file_lines": 5}), patch.object(verify, "load", return_value={"max_file_lines": 5}):
            self.assertEqual(verify.line_limits(["ai/services/coding/verify.py"])["status"], "FAILED")


class ToolTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username="member", password="pw12345!")
        self.admin = User.objects.create_user(username="admin", password="pw12345!")
        profile = AuthWorkflowService.get_profile(self.admin)
        profile.is_sysadmin = True
        profile.save()

    def test_tools_are_registered_as_code_tools(self):
        for name in ("app_coding_context", "app_plan_files", "app_repo_index"):
            self.assertIn(name, CODE_TOOLS)
            self.assertIn(name, AI_TOOL_REGISTRY)

    def test_members_get_no_code_and_do_not_even_see_the_tools(self):
        for fn, params in ((tools.coding_context, {"task": "x"}), (tools.plan_files, {"files": ["a.py"]}), (tools.repo_index, {"query": "x"})):
            self.assertIn("error", fn(self.member, params))
        offered = {s["function"]["name"] for s in investigation_tool_schemas(self.member)}
        self.assertFalse({"app_coding_context", "app_plan_files", "app_repo_index"} & offered)
        offered_admin = {s["function"]["name"] for s in investigation_tool_schemas(self.admin)}
        self.assertTrue({"app_coding_context", "app_plan_files", "app_repo_index"} <= offered_admin)

    def test_sysadmin_gets_real_answers(self):
        self.assertTrue(tools.plan_files(self.admin, {"files": ["db.sqlite3"]})["needs_owner_approval"])
        self.assertTrue(tools.repo_index(self.admin, {"query": "ExpenseService", "callers": True})["callers"])
        self.assertIn("skills", tools.coding_context(self.admin, {"task": "expenses"}))
        self.assertIn("error", tools.plan_files(self.admin, {"files": []}))
