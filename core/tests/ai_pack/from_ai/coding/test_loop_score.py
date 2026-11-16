"""Scoring of real agent runs (a real Agent with a scripted model writes the ledger and the trace) and the decision between two models."""

from ai.dev_agent.tests.fakes import edit, final, plan, tool
from ai.services.coding.training import loop_report, loop_score
from ai.tests.coding.traj_helper import FAIL, TrajRepo

READ = tool("read_file", path="app/calc.py")
RUN = {"returncode": 0, "seconds": 12.34, "timed_out": False, "tail": ""}
QA = {"task_id": "t-qa", "kind": "qa", "goal": "how does add work?", "answer": "add returns a + b, see app/calc.py"}
PATCH = {"task_id": "t-patch", "kind": "patch", "goal": "add a sub function", "answer": ""}
PLAN = plan(summary="add sub", steps=[{"title": "add sub", "files": ["app/calc.py"]}])
ADD_SUB = edit({"path": "app/calc.py", "replacements": [{"old": "    return a + b\n", "new": "    return a + b\n\n\ndef sub(a, b):\n    return a - b\n"}]})
CFG = {"eval_min_gain_points": 10, "eval_max_slower_percent": 20, "eval_min_tasks": 10}


class ScoreRunTests(TrajRepo):
    def score(self, task=QA, **run):
        return loop_score.score_task(self.root, task, {**RUN, **run})

    def test_an_answer_after_reading_a_file_is_done(self):
        self.ask(QA["goal"], [READ, final("add returns a + b (app/calc.py)")])
        row = self.score()
        self.assertEqual((row["success"], row["why"], row["status"], row["tool_calls"], row["seconds"]), (True, "", "answered", 1, 12.3))
        self.assertEqual((row["path_overlap"], row["cited_missing"], row["invalid_replies"]), (1.0, [], 0))
        self.assertGreater(row["tokens"], 0)

    def test_an_answer_that_read_nothing_is_not_done(self):
        self.ask(QA["goal"], [final("I think it adds two numbers")])
        row = self.score()
        self.assertEqual((row["success"], row["why"]), (False, "answered without reading anything"))

    def test_an_answer_citing_a_file_that_does_not_exist_is_not_done(self):
        self.ask(QA["goal"], [READ, final("add lives in app/ghost.py")])
        row = self.score()
        self.assertEqual((row["success"], row["cited_missing"], row["path_overlap"]), (False, ["app/ghost.py"], 0.0))
        self.assertIn("app/ghost.py", row["why"])

    def test_a_model_that_only_produces_invalid_replies_is_stopped_and_the_nudges_are_counted(self):
        self.ask(QA["goal"], ["Let me read the file first.", "I will look.", "Reading now."])
        row = self.score()
        self.assertEqual((row["success"], row["status"], row["invalid_replies"]), (False, "stopped", 2))
        self.assertTrue(row["why"].startswith("stopped: "))

    def test_a_question_answered_with_a_plan_is_not_done(self):
        self.agent([READ, PLAN]).plan(QA["goal"])
        row = self.score()
        self.assertEqual((row["success"], row["why"]), (False, "proposed changes for a question"))

    def test_a_verified_patch_is_done_and_one_answered_in_words_is_not(self):
        self.patch_run(PATCH["goal"], [READ, PLAN, READ, ADD_SUB, final("added sub()")])
        row = self.score(PATCH)
        self.assertEqual((row["success"], row["status"], row["why"]), (True, "completed", ""))

    def test_a_patch_whose_final_checks_failed_is_not_done(self):
        self.patch_run(PATCH["goal"], [READ, PLAN, READ, ADD_SUB, final("added sub()")], checks=(FAIL,))
        row = self.score(PATCH)
        self.assertEqual((row["success"], row["status"]), (False, "stopped"))
        self.assertTrue(row["why"].startswith("stopped: "))

    def test_a_patch_task_answered_in_words_instead_of_a_plan_is_not_done(self):
        self.ask(PATCH["goal"], [READ, final("you could add a sub function")])
        row = self.score(PATCH)
        self.assertEqual((row["success"], row["why"]), (False, "answered in words instead of making a plan"))

    def test_a_patch_that_touched_a_protected_file_is_never_done(self):
        money = tool("read_file", path="app/money.py")
        plan_money = plan(summary="touch money", files_edit=["app/money.py"], steps=[{"title": "edit", "files": ["app/money.py"]}])
        change = edit({"path": "app/money.py", "replacements": [{"old": "BALANCE = 1", "new": "BALANCE = 2"}]})
        self.patch_run("change the balance", [money, plan_money, money, change, final("changed")], approve=True)
        row = self.score({**PATCH, "task_id": "t-money"})
        self.assertEqual((row["success"], row["protected_touches"]), (False, ["app/money.py"]))
        self.assertIn("protected", row["why"])

    def test_a_timeout_and_a_missing_task_folder_are_results_not_crashes(self):
        row = self.score(timed_out=True, returncode=-1, tail="")
        self.assertEqual((row["success"], row["status"], row["why"]), (False, "no_task_folder", "timed out"))
        row = self.score(returncode=2, tail="error: no model set")
        self.assertIn("exit code 2", row["why"])
        self.assertIn("no model set", row["why"])
        self.ask(QA["goal"], [READ, final("add returns a + b (app/calc.py)")])
        self.assertEqual(self.score(timed_out=True, returncode=-1)["why"], "timed out", "a run cut off by the timeout is not done even if a ledger exists")


def summary(model, qa=(4, 5), patch=(2, 5), **extra):
    done = qa[0] + patch[0]
    return {"model": model, "tasks": 10, "success": done, "success_pct": done * 10.0, "qa": {"success": qa[0], "tasks": qa[1]}, "patch": {"success": patch[0], "tasks": patch[1]},
            "protected_touches": 0, "timeouts": 0, "invalid_replies": 0, "median_seconds": 100.0, **extra}


class VerdictTests(TrajRepo):
    def test_a_clear_win_needs_more_done_in_total_and_not_less_in_either_kind(self):
        won, text = loop_score.verdict(summary("old"), summary("new", qa=(5, 5), patch=(4, 5)), CFG)
        self.assertEqual((won, text), (True, "NEW MODEL WINS on real agent-loop tasks"))

    def test_too_few_tasks_decide_nothing(self):
        won, text = loop_score.verdict(summary("old", tasks=6), summary("new", qa=(5, 5), patch=(5, 5)), CFG)
        self.assertEqual(won, False)
        self.assertTrue(text.startswith("NOT ENOUGH TASKS: 6 real tasks"))

    def test_each_way_to_lose_is_named(self):
        cases = {
            "only +0.0 points": summary("new"),
            "only +5.0 points": summary("new", qa=(5, 5), patch=(2, 5)) | {"success_pct": 65.0},
            "worse on qa tasks (3 done against 4)": summary("new", qa=(3, 5), patch=(5, 5)),
            "worse on patch tasks (1 done against 2)": summary("new", qa=(5, 5), patch=(1, 5)),
            "touched protected files": summary("new", qa=(5, 5), patch=(4, 5), protected_touches=1),
            "30% slower": summary("new", qa=(5, 5), patch=(4, 5), median_seconds=130.0),
        }
        for expect, new in cases.items():
            won, text = loop_score.verdict(summary("old"), new, CFG)
            self.assertFalse(won, expect)
            self.assertTrue(text.startswith("NO WIN: ") and expect in text, (expect, text))

    def test_the_report_lists_every_task_for_both_models_and_says_nothing_was_switched(self):
        row = {"task_id": "t1", "kind": "qa", "timed_out": False, "protected_touches": [], "invalid_replies": 0, "status": "answered"}
        rows = {"old": [{**row, "success": True, "seconds": 5.0, "why": ""}],
                "new": [{**row, "success": False, "seconds": 7.0, "why": "stopped: no valid reply", "status": "stopped"}]}
        sums = [loop_score.summarize("old", rows["old"]), loop_score.summarize("new", rows["new"])]
        text = loop_report.report_text(sums, rows, "NO WIN: x", "D:/out")
        for part in ("t1 (qa)", "DONE 5s", "FAIL 7s: stopped: no valid reply", "NO WIN: x", "Nothing was switched in Settings", "D:/out"):
            self.assertIn(part, text)
