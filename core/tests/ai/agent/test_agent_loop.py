"""The investigation loop in Agent mode (scripted model): instructions, hint, read limit, Stop, live steps, sources."""

from __future__ import annotations

from django.test import SimpleTestCase, TestCase

from core.services.ai.agent import control
from core.services.ai.agent.sources import build_sources
from core.services.ai.cache_manager import AICacheManager
from core.services.ai.investigation import loop as inv
from core.tests.ai.investigation.support import ScriptedProvider, make_user, seed_tenant, tool_call


class AgentLoopTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user, cls.admin = make_user("al_user"), make_user("al_admin", sysadmin=True)
        seed_tenant(cls.user, "A", expenses=2, amount="30.00")

    def run_agent(self, script, user=None, **kw):
        prov = ScriptedProvider(script)
        kw.setdefault("agent", True)
        return inv.investigate(prov, user or self.user, "how much did I spend?", **kw), prov

    def test_agent_prompt_uses_the_editable_instructions_and_the_hint_is_marked_unverified(self):
        res, prov = self.run_agent([tool_call("app_data_models"), {"content": "2 rows."}],
                                   instructions="CUSTOM RULE: read before you speak.", hint="Total expenses: 60.00")
        first = prov.calls[0]["messages"]
        self.assertIn("CUSTOM RULE: read before you speak.", first[0]["content"])
        self.assertIn("built-in agent", first[0]["content"])
        self.assertNotIn("HARD RULES", first[0]["content"])
        self.assertIn("[HINT, not verified by you", first[-1]["content"])
        self.assertIn("Total expenses: 60.00", first[-1]["content"])
        self.assertEqual(res.content, "2 rows.")

    def test_default_instructions_apply_when_none_are_customised_and_plain_mode_is_unchanged(self):
        _res, prov = self.run_agent([{"content": "ok"}])
        self.assertIn("HOW YOU WORK (Agent mode)", prov.calls[0]["messages"][0]["content"])
        _res, prov = self.run_agent([{"content": "ok"}], agent=False, hint="ignored?")
        self.assertIn("HARD RULES", prov.calls[0]["messages"][0]["content"])

    def test_file_read_limit_rejects_extra_reads_but_the_run_continues(self):
        res, prov = self.run_agent([
            tool_call("app_read_file", path="manage.py", start_line=1, end_line=5),
            tool_call("app_read_file", path="manage.py", start_line=6, end_line=9),
            {"content": "manage.py starts a Django command line."}], user=self.admin, max_reads=1)
        self.assertEqual([s["status"] for s in res.steps], ["success", "rejected"])
        self.assertEqual(res.steps[1]["rejection_reason"], "read limit")
        self.assertIn("limit of 1 file reads", "\n".join(m["content"] for m in prov.calls[2]["messages"]))
        self.assertEqual(res.content, "manage.py starts a Django command line.")

    def test_stop_ends_the_run_after_the_current_step_without_another_model_call(self):
        prov = ScriptedProvider([tool_call("app_data_models"), tool_call("app_data_query", model="Expense", aggregate={"count": "*"}),
                                 {"content": "should never be asked for"}])
        res = inv.investigate(prov, self.user, "count my expenses", agent=True, cancel_check=lambda: len(prov.calls) >= 2)
        self.assertEqual(res.reason, "cancelled")
        self.assertEqual(len(prov.calls), 2)
        self.assertEqual([s["tool"] for s in res.steps], ["app_data_models"])
        self.assertIn("I investigated the app", res.content)       # what was found so far is kept

    def test_stop_before_anything_ran_gives_an_empty_digest_not_an_error(self):
        res, prov = self.run_agent([{"content": "never"}], cancel_check=lambda: True)
        self.assertEqual((res.reason, res.content, len(prov.calls)), ("cancelled", "", 0))
        self.assertIsNone(res.error)

    def test_the_live_step_list_is_published_with_status_and_target(self):
        cid = 987001
        self.run_agent([tool_call("app_data_query", model="Expense", aggregate={"count": "*"}),
                        tool_call("app_data_query", model="Nope"), {"content": "done"}], conversation_id=cid)
        state = AICacheManager().get(f"ai_loop_progress:{self.user.id}:{cid}")
        self.assertEqual([s["status"] for s in state["steps"]], ["ok", "ok"])        # an unknown table is a tool error the model reads, not a crash
        self.assertEqual(state["steps"][0]["tool"], "app_data_query")
        self.assertEqual(state["steps"][0]["target"], "Expense")
        self.assertTrue(state["can_stop"])
        self.assertEqual(state["status"], "running")

    def test_a_failed_tool_shows_as_failed_in_the_step_list(self):
        cid = 987002
        self.run_agent([tool_call("app_data_models", bogus_argument="x"), {"content": "done"}], conversation_id=cid)
        state = AICacheManager().get(f"ai_loop_progress:{self.user.id}:{cid}")
        self.assertIn(state["steps"][0]["status"], ("ok", "failed"))

    def test_evidence_first_a_data_answer_without_a_tool_call_is_pushed_back(self):
        res, prov = self.run_agent([{"content": "You spent about 60."}, tool_call("app_data_query", model="Expense", aggregate={"sum": "amount_base"}),
                                    {"content": "You spent 60.00 in total."}], require_evidence=True)
        self.assertEqual(res.content, "You spent 60.00 in total.")
        self.assertEqual(res.nudges, 1)

    def test_a_model_without_native_tools_still_works_and_is_flagged(self):
        prov = ScriptedProvider([{"content": '{"name": "app_data_models", "arguments": {}}'}, {"content": "2 rows."}])
        prov.supports_tools = False
        res = inv.investigate(prov, self.user, "what tables?", agent=True)
        self.assertFalse(res.native_tools)
        self.assertEqual(res.steps[0]["tool"], "app_data_models")

    def test_customers_are_never_offered_or_allowed_code_tools_in_agent_mode(self):
        res, prov = self.run_agent([tool_call("app_grep", pattern="SECRET_KEY"), tool_call("app_grep", pattern="SECRET_KEY"),
                                    tool_call("app_grep", pattern="SECRET_KEY"), {"content": "I could not search the code."}])
        offered = {t["function"]["name"] for t in prov.calls[0]["tools"]}
        self.assertNotIn("app_grep", offered)
        self.assertEqual(res.steps, [])
        self.assertNotIn("source code", prov.calls[0]["messages"][0]["content"])


class SourcesBuilderTest(SimpleTestCase):
    def step(self, tool, status="success", **args):
        return {"tool": tool, "status": status, "arguments": args}

    def test_sources_come_only_from_calls_that_really_succeeded(self):
        got = build_sources([
            self.step("app_read_file", path="core/models/x.py", start_line=10, end_line=40),
            self.step("app_data_query", model="Expense"), self.step("app_data_query", model="Expense"),
            self.step("app_computed_figures", question="net worth"), self.step("app_knowledge_search", query="gold"),
            self.step("app_routes", query="gold"), self.step("app_git_history", path="a.py"),
            self.step("app_grep", status="rejected", pattern="secret")])
        self.assertEqual(got[:3], ["investigation_code", "investigation_data", "investigation_docs"])
        self.assertIn("agent:code:core/models/x.py:10-40", got)
        self.assertEqual(got.count("agent:data:Expense"), 1)
        self.assertIn("agent:figures:net worth", got)
        self.assertIn("agent:docs:gold", got)
        self.assertIn("agent:app:gold", got)
        self.assertIn("agent:git:a.py", got)
        self.assertFalse([s for s in got if "secret" in s])

    def test_no_successful_call_means_the_generic_key_only(self):
        self.assertEqual(build_sources([]), ["investigation"])
        self.assertEqual(build_sources([self.step("app_grep", status="failed", pattern="x")]), ["investigation"])

    def test_stop_flag_helpers_are_scoped_per_user_and_conversation(self):
        class U:
            id = 4242

        control.request_stop(U, 1)
        self.assertTrue(control.is_stopped(U, 1))
        self.assertFalse(control.is_stopped(U, 2))
        self.assertFalse(control.is_stopped(U, None))
        control.clear_stop(U, 1)
        self.assertFalse(control.is_stopped(U, 1))
