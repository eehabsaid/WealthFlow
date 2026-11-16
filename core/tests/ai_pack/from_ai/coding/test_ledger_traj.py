"""Trajectory examples from REAL agent runs: a scripted model drives the real Agent in a throw-away project, and the extractor must give back exactly the
conversation the provider received - or drop the phase with a counted reason, never repair or invent anything."""

from ai.dev_agent.engine.protocol import system_prompt
from ai.dev_agent.tests.fakes import final, tool
from ai.services.coding.training import ledger_traj as traj
from ai.tests.coding.traj_helper import TrajRepo

ANSWER = "add returns a + b; see app/calc.py"
READS = [tool("read_file", path="app/calc.py"), tool("grep", pattern="def add")]


class QuestionExamplesTests(TrajRepo):
    def one(self):
        found = traj.extract()
        self.assertEqual(len(found["candidates"]), 1, dict(found["stats"]))
        return found["candidates"][0]

    def test_a_question_becomes_one_example_identical_to_what_the_model_received(self):
        ledger = self.ask("how does add work?", [*READS, final(ANSWER)])
        ex = self.one()
        system, sent = self.provider.calls[-1]
        self.assertEqual(ex["messages"][:-1], [{"role": "system", "content": system}, *sent])
        self.assertEqual(ex["messages"][-1], {"role": "assistant", "content": final(ANSWER)})
        self.assertEqual(system, system_prompt(True))
        self.assertEqual([m["role"] for m in ex["messages"]], ["system", "user", "assistant", "user", "assistant", "user", "assistant"])
        self.assertEqual((ex["kind"], ex["task_kind"], ex["label"], ex["key"]), ("traj", "qa", "plan", f"{ledger.id}#0"))
        self.assertEqual((ex["tools"], ex["answer"], ex["steps"]), (["read_file", "grep"], ANSWER, 3))
        self.assertEqual(ex["checks"]["replay"], "ok")
        self.assertEqual((ex["checks"]["repo"]["checked"], ex["checks"]["repo"]["same"]), (1, 1))

    def test_the_results_in_the_example_are_the_real_file_not_a_summary(self):
        self.ask("how does add work?", [*READS, final(ANSWER)])
        result = self.one()["messages"][3]["content"]
        self.assertTrue(result.startswith("TOOL RESULT read_file:\n"))
        self.assertIn("def add(a, b):", result)
        self.assertIn("return a + b", result)

    def test_a_path_in_the_answer_that_is_not_in_the_repo_is_flagged_for_the_reviewer(self):
        self.ask("where is it?", [*READS, final("see app/calc.py and app/ghost.py")])
        self.assertEqual(self.one()["checks"]["cited_missing"], ["app/ghost.py"])

    def test_a_task_without_a_trace_is_counted_and_never_guessed_from_its_ledger(self):
        self.qa_task("old question", "an answer from before the trace upgrade")
        found = traj.extract()
        self.assertEqual(found["candidates"], [])
        self.assertEqual(found["stats"]["dropped:task_without_trace"], 1)

    def test_a_task_that_did_not_finish_well_teaches_nothing(self):
        ledger = self.ask("how does add work?", ["not json", "still not json", "no json again"])
        self.assertEqual(ledger.data["status"], "stopped")
        found = traj.extract()
        self.assertEqual((found["candidates"], found["stats"]["dropped:task_not_finished_well"]), ([], 1))

    def test_a_phase_that_needed_a_nudge_is_not_an_example_even_though_the_task_ended_well(self):
        ledger = self.ask("how does add work?", [READS[0], "this is not json", final(ANSWER)])
        self.assertEqual(ledger.data["status"], "answered")
        found = traj.extract()
        self.assertEqual((found["candidates"], found["stats"]["dropped:phase_not_clean"]), ([], 1))

    def test_an_answer_without_a_single_tool_call_is_not_an_example_of_the_agent_loop(self):
        self.ask("how does add work?", [final("I think it adds")])
        found = traj.extract()
        self.assertEqual((found["candidates"], found["stats"]["dropped:too_few_tool_calls"]), ([], 1))

    def test_a_run_with_too_many_failing_tool_calls_is_dropped(self):
        bad = [tool("read_file", path=f"app/missing{i}.py") for i in range(3)]
        self.ask("how does add work?", [*bad, final(ANSWER)])
        self.assertEqual(traj.extract()["stats"]["dropped:too_many_tool_errors"], 1)

    def test_the_same_question_answered_the_same_way_twice_is_kept_once(self):
        for _ in range(2):
            self.ask("how does add work?", [*READS, final(ANSWER)])
        found = traj.extract()
        self.assertEqual((len(found["candidates"]), found["stats"]["dropped:duplicate"], found["stats"]["tasks"]), (1, 1, 2))


class RepoCheckTests(TrajRepo):
    def run_question(self):
        self.ask("how does add work?", [*READS, final(ANSWER)])

    def test_a_file_that_changed_since_the_task_drops_the_example(self):
        self.run_question()
        self.write("app/calc.py", "def add(a, b):\n    return a + b + 0\n")
        found = traj.extract()
        self.assertEqual((found["candidates"], found["stats"]["dropped:repo_changed"]), ([], 1))

    def test_a_file_that_was_deleted_since_the_task_drops_the_example(self):
        self.run_question()
        (self.root / "app/calc.py").unlink()
        self.assertEqual(traj.extract()["stats"]["dropped:repo_changed"], 1)

    def test_the_repo_check_can_be_switched_off_and_then_reports_what_changed(self):
        self.run_question()
        self.write("app/calc.py", "def add(a, b):\n    return a + b + 0\n")
        self.set_traj_config(require_repo_match=False)
        repo = traj.extract()["candidates"][0]["checks"]["repo"]
        self.assertEqual((repo["changed"], repo["same"]), (["app/calc.py"], 0))

    def test_an_example_longer_than_the_trainer_can_read_is_dropped_not_cut(self):
        self.run_question()
        self.set_traj_config(max_seq_tokens=50)
        found = traj.extract()
        self.assertEqual((found["candidates"], found["stats"]["dropped:too_long_for_trainer"]), ([], 1))

    def test_secrets_in_a_tool_result_never_reach_the_example(self):
        self.write("app/conf.py", 'API_KEY = "sk-live-0123456789abcdefghijklmn"\nSALARY = 12500.75\nHOST = "db.internal"\n')
        self.ask("what is configured?", [tool("read_file", path="app/conf.py"), final("it sets a key, a salary figure and a host in app/conf.py")])
        text = "\n".join(m["content"] for m in self.one_example()["messages"])
        self.assertNotIn("sk-live-0123456789abcdefghijklmn", text)
        self.assertIn("12500.75", text)   # a plain number is data, not a secret
        self.assertIn("db.internal", text)

    def one_example(self):
        found = traj.extract()
        self.assertEqual(len(found["candidates"]), 1, dict(found["stats"]))
        return found["candidates"][0]
