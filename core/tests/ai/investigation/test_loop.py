"""The investigation loop with a scripted model: tool use, refusal nudges, budgets, fallbacks, read-only guarantee."""

from __future__ import annotations

from django.test import SimpleTestCase, TestCase

from core.services.ai.investigation import loop as inv
from core.services.ai.investigation import loop_helpers

from .support import ScriptedProvider, make_user, seed_tenant, tool_call


class LoopTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user("loop_user")
        cls.admin = make_user("loop_admin", sysadmin=True)
        seed_tenant(cls.user, "L", expenses=4, amount="25.00")

    def run_loop(self, script, user=None, **kw):
        prov = ScriptedProvider(script)
        return inv.investigate(prov, user or self.user, "how much did I spend?", **kw), prov

    def test_tool_call_then_answer_uses_the_real_result(self):
        res, prov = self.run_loop([
            tool_call("app_data_query", model="Expense", aggregate={"sum": "amount_base"}),
            {"content": "You spent 100.00 in total."}])
        self.assertEqual(res.content, "You spent 100.00 in total.")
        self.assertEqual([s["tool"] for s in res.steps], ["app_data_query"])
        self.assertEqual(res.steps[0]["status"], "success")
        seen = "\n".join(m["content"] for m in prov.calls[1]["messages"])
        self.assertIn("TOOL RESULT (app_data_query", seen)
        self.assertIn('"sum_amount_base":"100"', seen)
        self.assertEqual(prov.calls[0]["kwargs"]["temperature"], 0.1)

    def test_json_in_text_is_executed_when_the_model_has_no_native_tools(self):
        prov = ScriptedProvider([
            {"content": 'Let me look.\n{"name": "app_data_models", "arguments": {"model": "expense"}}'},
            {"content": "Expense has 4 rows."}])
        prov.supports_tools = False
        res = inv.investigate(prov, self.user, "what tables exist?")
        self.assertEqual(res.content, "Expense has 4 rows.")
        self.assertEqual(res.steps[0]["tool"], "app_data_models")
        self.assertIsNone(prov.calls[0]["tools"])
        self.assertIn('{"name": "<tool>"', prov.calls[0]["messages"][0]["content"])   # text protocol explained

    def test_refusal_is_rejected_and_the_model_is_pushed_to_investigate(self):
        res, prov = self.run_loop([
            {"content": "I don't have access to your expense data."},
            tool_call("app_data_models"),
            {"content": "You have 4 expenses."}])
        self.assertEqual(res.content, "You have 4 expenses.")
        self.assertEqual(res.nudges, 1)
        nudge = prov.calls[1]["messages"][-1]["content"]
        self.assertIn("DO have full read access", nudge)
        self.assertNotIn("I don't have access", "\n".join(m["content"] for m in prov.calls[1]["messages"] if m["role"] == "assistant"))

    def test_announcing_the_next_step_is_pushed_to_act_not_accepted_as_the_answer(self):
        res, prov = self.run_loop([
            tool_call("app_data_models"),
            {"content": "Now I have a comprehensive picture. Let me generate the Word document."},
            tool_call("generate_file", format="docx", title="Guide", content="# Guide\n\nWealthFlow tracks your money."),
            {"content": "I created the user guide."}])
        self.assertEqual(res.content, "I created the user guide.")
        self.assertEqual([s["tool"] for s in res.steps], ["app_data_models", "generate_file"])
        pushed = "\n".join(m["content"] for m in prov.calls[2]["messages"])
        self.assertIn("announced a next step", pushed)
        self.assertIn("`content`", pushed)

    def test_negative_finding_after_investigating_is_a_valid_answer(self):
        res, _ = self.run_loop([tool_call("app_data_query", model="Expense", filters={"year": 1999}),
                                {"content": "I couldn't find any expense in 1999: Expense has 0 rows for that year."}])
        self.assertIn("0 rows", res.content)
        self.assertEqual(res.nudges, 0)

    def test_evidence_required_blocks_answers_from_imagination(self):
        res, _ = self.run_loop([{"content": "It is implemented in utils.py."}, tool_call("app_data_models"),
                                {"content": "Based on the tables: Expense."}], require_evidence=True)
        self.assertEqual(res.nudges, 1)
        self.assertEqual(len(res.steps), 1)

    def test_empty_reply_is_nudged(self):
        res, _ = self.run_loop([{"content": ""}, {"content": "Done: nothing to add."}])
        self.assertEqual((res.nudges, res.content), (1, "Done: nothing to add."))

    def test_duplicate_calls_are_blocked_not_reexecuted(self):
        same = tool_call("app_data_models")
        res, prov = self.run_loop([same, same, {"content": "Tables listed."}])
        self.assertEqual(len(res.steps), 1)
        self.assertIn("exact call", "\n".join(m["content"] for m in prov.calls[2]["messages"]))

    def test_unoffered_tools_are_never_executed_read_only_guarantee(self):
        for name in ("create_scenario", "app_grep", "validate_and_execute_tool"):   # modify-tier / code tool for a customer
            res, prov = self.run_loop([tool_call(name, pattern="x", scenario="y"), {"content": "Answer from data."}])
            self.assertEqual(res.steps, [], name)
            self.assertIn("not available", prov.calls[1]["messages"][-1]["content"], name)

    def test_customer_never_gets_code_tools_but_sysadmin_does(self):
        _, p1 = self.run_loop([{"content": "ok"}])
        _, p2 = self.run_loop([{"content": "ok"}], user=self.admin)
        offered = lambda p: {t["function"]["name"] for t in p.calls[0]["tools"]}   # noqa: E731
        self.assertFalse(offered(p1) & {"app_grep", "app_read_file", "app_list_dir", "app_find_files", "app_find_definition"})
        self.assertIn("app_grep", offered(p2))
        self.assertNotIn("SOURCE MAP", p1.calls[0]["messages"][0]["content"])
        self.assertIn("SOURCE MAP", p2.calls[0]["messages"][0]["content"])

    def test_step_limit_forces_a_tool_free_final_answer(self):
        script = [tool_call("app_data_query", model="Expense", limit=i + 1) for i in range(3)] + [{"content": "Final from evidence."}]
        res, prov = self.run_loop(script, max_steps=3)
        self.assertEqual((res.reason, res.content, len(res.steps)), ("max_steps", "Final from evidence.", 3))
        self.assertIsNone(prov.calls[-1]["tools"])

    def test_tool_request_in_the_forced_final_call_becomes_a_digest_not_raw_json(self):
        script = [tool_call("app_data_models"), tool_call("app_data_models", model="Bank"),
                  {"content": '{"name": "app_data_models", "arguments": {}}'}]
        res, _ = self.run_loop(script, max_steps=2)
        self.assertIn("This is what I found", res.content)
        self.assertNotIn('"arguments"', res.content.split("This is what I found")[0])

    def test_time_budget_forces_a_tool_free_final_answer(self):
        res, prov = self.run_loop([{"content": "Written without exploring."}], budget_s=5)
        self.assertEqual(res.reason, "budget")
        self.assertEqual(res.content, "Written without exploring.")
        self.assertIsNone(prov.calls[0]["tools"])

    def test_provider_error_without_evidence_reports_the_error(self):
        res, _ = self.run_loop([{"error": "connection refused"}])
        self.assertEqual((res.content, res.error, res.reason), ("", "connection refused", "provider_error"))

    def test_provider_error_after_evidence_returns_an_honest_digest(self):
        res, _ = self.run_loop([tool_call("app_data_models"), {"error": "timeout"}, {"error": "timeout"}])
        self.assertIn("could not finish the write-up", res.content)
        self.assertIn("app_data_models", res.content)

    def test_final_refusal_after_evidence_falls_back_to_digest(self):
        res, _ = self.run_loop([tool_call("app_data_models")] + [{"content": "I cannot access that."}] * 4)
        self.assertIn("This is what I found", res.content)

    def test_a_cut_off_generate_file_call_is_never_the_answer(self):
        cut = 'Calling generate_file({"content": "# Guide\\n\\n## Intro\\n\\nWelcome to the app and its screens'
        res, _ = self.run_loop([{"content": cut}], user=self.admin)
        self.assertEqual(res.reason, "truncated_call")
        self.assertTrue(res.content.startswith("# Guide"))
        self.assertNotIn("Calling", res.content)

    def test_a_call_written_as_text_after_a_long_introduction_is_never_the_answer(self):
        text = ("Now I have enough material. Let me compose the comprehensive Arabic user guide and generate the Word document.\n\n"
                'Calling generate_file({"content":"# Guide\\n\\n## Intro\\n\\nWelcome","filename":"a.docx","format","docx"}')
        res, _ = self.run_loop([{"content": text}], user=self.admin)
        self.assertEqual(res.reason, "truncated_call")
        self.assertTrue(res.content.startswith("# Guide"))
        self.assertNotIn("Calling", res.content)

    def test_another_unreadable_tool_call_text_is_nudged_then_never_shown(self):
        res, prov = self.run_loop([{"content": 'Calling app_grep({"pattern": "x"'}, tool_call("app_data_models"),
                                   {"content": "You have 4 expenses."}])
        self.assertEqual(res.content, "You have 4 expenses.")
        self.assertIn("could not be read", prov.calls[1]["messages"][-1]["content"])
        res, _ = self.run_loop([{"content": 'Calling app_grep({"pattern": "x"'}] * 5)
        self.assertNotIn("Calling app_grep", res.content)

    def test_history_is_trimmed_and_included(self):
        hist = [{"role": "user", "content": f"q{i}"} for i in range(9)]
        _, prov = self.run_loop([{"content": "ok"}], history=hist)
        sent = [m["content"] for m in prov.calls[0]["messages"] if m["role"] == "user"]
        self.assertEqual(sent, ["q5", "q6", "q7", "q8", "how much did I spend?"])


class HelpersTest(SimpleTestCase):
    def test_compaction_trims_oldest_tool_results_first(self):
        msgs = [{"role": "system", "content": "SYS"}] + [
            {"role": "system", "content": f"TOOL RESULT (t{i} x):\n" + "z" * 3000} for i in range(4)]
        loop_helpers.compact(msgs, 7000)
        self.assertIn("trimmed", msgs[1]["content"])
        self.assertIn("trimmed", msgs[2]["content"])
        self.assertNotIn("trimmed", msgs[4]["content"])
        self.assertEqual(msgs[0]["content"], "SYS")

    def test_result_text_is_capped_with_a_hint(self):
        out = loop_helpers.result_text({"ok": True, "data": {"rows": ["x" * 100] * 100}}, 500)
        self.assertLess(len(out), 700)
        self.assertIn("narrow the call", out)
        self.assertIn("tool boom", loop_helpers.result_text({"ok": False, "error": "tool boom"}, 500))
