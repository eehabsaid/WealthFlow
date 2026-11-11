"""Ledger-based training examples: completed/verified dev-agent tasks (not git history) become QA and patch examples."""

from ai.dev_agent.engine import verify
from ai.dev_agent.ledger.ledger import Ledger
from ai.services.coding.training import ledger_examples as le
from ai.tests.coding.ledger_helper import LedgerRepo


class QaCandidateTests(LedgerRepo):
    def test_an_answered_task_becomes_an_example(self):
        ledger = self.qa_task("how does X work", "X works by doing Y.")
        ex, why = le.qa_candidate(ledger.data, self.qa_cfg())
        self.assertEqual(why, "")
        self.assertEqual(ex["messages"][1]["content"], "QUESTION: how does X work")
        self.assertEqual(ex["messages"][2]["content"], "X works by doing Y.")

    def test_a_task_without_a_final_answer_is_dropped(self):
        for status in ("stopped", "rejected", "completed", "planning"):
            ex, why = le.qa_candidate({"id": "t", "status": status, "goal": "g", "answer": "a"}, self.qa_cfg())
            self.assertIsNone(ex)
            self.assertEqual(why, "not_answered")

    def test_an_empty_answer_is_dropped(self):
        ex, why = le.qa_candidate({"id": "t", "status": "answered", "goal": "g", "answer": "   "}, self.qa_cfg())
        self.assertEqual(why, "empty_goal_or_answer")

    def test_secrets_and_pii_in_the_answer_are_redacted(self):
        ledger = self.qa_task("contact info", "email me at a@b.com, call 555-123-4567, it costs $42.50; password='hunter2hunter2'")
        ex, why = le.qa_candidate(ledger.data, self.qa_cfg())
        self.assertEqual(why, "")
        for leak in ("a@b.com", "555-123-4567", "$42.50", "hunter2hunter2"):
            self.assertNotIn(leak, ex["messages"][2]["content"])
        self.assertGreater(ex["redactions"], 0)

    def test_extract_scans_real_tasks_on_disk(self):
        self.qa_task("q1", "a1")
        self.qa_task("q2", "a2")
        patch_ledger = self.patch_task("not a qa task", {"app/x.py": (None, "x = 1\n")})  # a completed task should never show up as a qa candidate
        result = le.extract("qa")
        self.assertEqual(result["stats"]["candidates"], 2)
        self.assertEqual({c["goal"] for c in result["candidates"]}, {"q1", "q2"})
        self.assertNotIn(patch_ledger.id, {c["task_id"] for c in result["candidates"]})


class PatchCandidateTests(LedgerRepo):
    def test_a_completed_verified_task_becomes_an_example(self):
        ledger = self.patch_task("add a helper", {"app/calc.py": ("def add(a, b):\n    return a + b\n", "def add(a, b):\n    return a + b + 0\n")})
        ex, why = le.patch_candidate(ledger, self.patch_cfg())
        self.assertEqual(why, "")
        self.assertEqual(ex["files"], ["app/calc.py"])
        self.assertIn("+    return a + b + 0", ex["diff"])
        self.assertIn("def add(a, b):", ex["messages"][1]["content"])   # the "before" content is in the prompt

    def test_an_unverified_task_is_dropped(self):
        ledger = self.patch_task("add a helper", {"app/calc.py": ("x = 1\n", "x = 2\n")}, verified=False)
        ex, why = le.patch_candidate(ledger, self.patch_cfg())
        self.assertIsNone(ex)
        self.assertEqual(why, "not_verified")

    def test_a_task_without_a_frozen_diff_is_dropped(self):
        ledger = Ledger.create(self.project, "old task before point 3")
        ledger.record_file("app/calc.py", "written", "s1", "s2")
        ledger.add_verification("final", [{"step": "tests", "status": "PASSED"}])
        ledger.set_status("completed")   # no freeze_result_diffs(): simulates a task that predates the after-snapshot capture
        ex, why = le.patch_candidate(ledger, self.patch_cfg())
        self.assertIsNone(ex)
        self.assertEqual(why, "no_source_diff")

    def test_a_task_touching_a_protected_file_is_dropped(self):
        ledger = self.patch_task("touch balances", {"app/money.py": ("BALANCE = 1\n", "BALANCE = 2\n")})
        ex, why = le.patch_candidate(ledger, self.patch_cfg())
        self.assertIsNone(ex)
        self.assertEqual(why, "protected_file")

    def test_a_new_file_shows_as_new_in_the_before_context(self):
        ledger = self.patch_task("add a file", {"app/new.py": (None, "VALUE = 1\n")})
        ex, _ = le.patch_candidate(ledger, self.patch_cfg())
        self.assertIn("(new file)", ex["messages"][1]["content"])

    def test_secrets_in_the_diff_are_redacted(self):
        ledger = self.patch_task("add a secret-looking line", {"app/calc.py": ("x = 1\n", 'x = 1\npassword = "hunter2hunter2"\n')})
        ex, why = le.patch_candidate(ledger, self.patch_cfg())
        self.assertEqual(why, "")
        self.assertNotIn("hunter2hunter2", ex["diff"])


class DedupTests(LedgerRepo):
    def test_exact_and_near_duplicate_answers_keep_only_the_first(self):
        self.qa_task("q1", "The answer is exactly forty two, always has been.")
        self.qa_task("q2", "The answer is exactly forty two, always has been.")   # exact duplicate answer
        self.qa_task("q3", "The answer is exactly forty two, always has been!")  # near duplicate (one punctuation mark)
        self.qa_task("q4", "Something completely different about routing.")
        result = le.extract("qa")
        self.assertEqual(result["stats"]["candidates"], 2)
        self.assertGreaterEqual(result["stats"]["dropped:duplicate_exact"] + result["stats"]["dropped:duplicate_near"], 2)


class OverallHelperTests(LedgerRepo):
    def test_verify_overall_matches_the_dev_agent_engine(self):
        self.assertEqual(verify.overall([{"step": "tests", "status": "PASSED"}]), "VERIFIED")
        self.assertEqual(verify.overall([{"step": "tests", "status": "FAILED"}]), "FAILED")
