"""Backlog item 3: schema coercion, shared rejections, tool-result token budget."""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from core.models import AppSettings
from core.services.ai.tools import validate_and_execute_tool
from core.services.ai.tools.rejections import make_rejection
from core.services.ai.tools.result_budget import compact_tool_result, tool_result_max_chars
from core.services.ai.tools.schema_validation import as_bool, coerce_and_validate
from core.tests.billing.test_support import grant_ai_workspace_access

SCHEMA = {"properties": {
    "flag": {"type": "boolean"}, "n": {"type": "integer"}, "x": {"type": "number"},
    "s": {"type": "string"}, "ids": {"type": "array", "items": {"type": "integer"}},
    "mode": {"type": "string", "enum": ["all", "portfolio"]},
}}


class CoerceTest(SimpleTestCase):
    def test_string_values_are_coerced(self):
        out, err = coerce_and_validate(SCHEMA, {"flag": "false", "n": "5", "x": "1.5", "ids": '["1", 2]', "s": 7, "mode": "ALL"})
        self.assertIsNone(err)
        self.assertEqual(out, {"flag": False, "n": 5, "x": 1.5, "ids": [1, 2], "s": "7", "mode": "all"})

    def test_bad_values_rejected(self):
        for params in ({"flag": "maybe"}, {"n": "abc"}, {"n": True}, {"x": "nan-ish"}, {"s": {"a": 1}},
                       {"ids": "not_a_list"}, {"ids": ["a"]}, {"mode": "zzz"}):
            _, err = coerce_and_validate(SCHEMA, params)
            self.assertIsNotNone(err, params)

    def test_unknown_and_none_pass_through(self):
        out, err = coerce_and_validate(SCHEMA, {"extra": object, "n": None})
        self.assertIsNone(err)
        self.assertIn("extra", out)

    def test_as_bool(self):
        self.assertFalse(as_bool("false"))
        self.assertTrue(as_bool("True"))
        self.assertFalse(as_bool(None))
        self.assertTrue(as_bool(None, True))


class RejectionTest(SimpleTestCase):
    def test_shape_matches_legacy_audit(self):
        audit, res = make_rejection("t", "ts", {"a": 1}, "why")
        self.assertEqual(audit, {"tool": "t", "timestamp": "ts", "status": "rejected", "duration_ms": 0,
                                 "rejection_reason": "why", "arguments": {"a": 1}})
        self.assertEqual(res, {"ok": False, "error": "why"})


class ResultBudgetTest(SimpleTestCase):
    def _big(self):
        return {"expenses": {"recent_expenses": [{"id": i, "d": "2026-01-01", "amt": 100 + i, "cat": "Food"} for i in range(500)],
                             "total": 12345},
                "instructions": "KEEP THIS RULE " * 20}

    def test_small_result_unchanged(self):
        res = {"a": 1, "b": [1, 2]}
        self.assertEqual(compact_tool_result(res, 1000), json.dumps(res, separators=(",", ":")))

    def test_big_list_is_cut_head_kept_and_flagged(self):
        out = json.loads(compact_tool_result(self._big(), 3000))
        kept = out["expenses"]["recent_expenses"]
        self.assertLess(len(kept), 500)
        self.assertEqual(kept[0]["id"], 0)  # newest-first head preserved
        self.assertEqual(out["expenses"]["total"], 12345)
        self.assertEqual(out["instructions"], self._big()["instructions"])
        self.assertEqual(out["_truncation"]["lists"]["expenses.recent_expenses"]["of"], 500)

    def test_result_fits_budget(self):
        self.assertLessEqual(len(compact_tool_result(self._big(), 3000)), 3000 + 700)

    def test_non_dict_hard_cut(self):
        out = compact_tool_result(["x" * 100] * 200, 500)
        self.assertTrue(out.endswith("[TRUNCATED]"))


class BudgetSettingTest(TestCase):
    def test_follows_context_budget_with_floor(self):
        AppSettings.set("ai_context_token_budget", "4096")
        self.assertEqual(tool_result_max_chars(), 4096 * 4)
        AppSettings.set("ai_context_token_budget", "100")
        self.assertEqual(tool_result_max_chars(), 4000)


class ExecutionCoercionTest(TestCase):
    def setUp(self):
        AppSettings.set("ai_read_only", "false")
        self.user = get_user_model().objects.create_user(username="item3_u", password="x")
        grant_ai_workspace_access(self.user)

    def test_string_false_force_refresh_does_not_force_crawl(self):
        with patch("core.services.ai.context_builder.AIContextBuilder.build_structure_context", return_value={"ok": 1}) as m:
            audit, res = validate_and_execute_tool("read_live_app_structure", {"force_refresh": "false"}, self.user)
        self.assertEqual(audit["status"], "success", res)
        self.assertFalse(m.call_args.kwargs["force_refresh"])

    def test_string_limit_and_wrong_type_rejected(self):
        audit, res = validate_and_execute_tool("query_application_data", {"search_query": "x", "limit": "many"}, self.user)
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("'limit'", res["error"])

    def test_string_scenario_ids_are_coerced_then_pass_type_check(self):
        audit, res = validate_and_execute_tool("compare_scenarios", {"scenario_ids": ["1", "2"]}, self.user)
        self.assertNotIn("must be integers", json.dumps(res))
