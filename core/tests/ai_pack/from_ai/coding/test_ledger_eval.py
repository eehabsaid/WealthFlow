"""Evaluation wiring for the ledger-based coding_agent model: QA and patch held-out examples are run together against the same two models,
patch is scored by code (reusing scoring.py's patch/protected-file checks), and the combined verdict is decided by patch alone - QA has no
code-checkable ground truth, so it never wins or loses a verdict on its own."""

from unittest.mock import patch

from django.test import SimpleTestCase

from ai.services.coding.training import ledger_eval, scoring


class QaScoringTests(SimpleTestCase):
    def test_an_empty_answer_scores_format_not_ok(self):
        row = ledger_eval.score_qa({"answer": "reference text"}, "")
        self.assertEqual(row["format_ok"], False)

    def test_an_identical_answer_scores_near_one(self):
        row = ledger_eval.score_qa({"answer": "the cache is keyed by user id"}, "the cache is keyed by user id")
        self.assertGreater(row["similarity"], 0.99)


class VerdictTests(SimpleTestCase):
    def cfg(self, **over):
        return {"eval_min_gain_points": 5, "eval_max_slower_percent": 20, **over}

    def summary(self, patch_tasks=5, tests_pass_pct=40.0, protected_touches=0, median_seconds=10.0, qa_tasks=3):
        return {"patch": {"tasks": patch_tasks, "tests_pass_pct": tests_pass_pct, "protected_touches": protected_touches, "median_seconds": median_seconds},
                "qa": {"tasks": qa_tasks, "avg_similarity": 0.5, "median_seconds": 5.0}}

    def test_verdict_needs_a_clear_win_and_no_new_problems(self):
        old = self.summary()
        win = self.summary(tests_pass_pct=60.0, median_seconds=11.0)
        self.assertTrue(ledger_eval.verdict(old, win, self.cfg())[0])
        for change, word in (({"tests_pass_pct": 42.0}, "points"), ({"protected_touches": 1}, "protected"), ({"median_seconds": 30.0}, "slower")):
            won, why = ledger_eval.verdict(old, self.summary(**{**{"tests_pass_pct": 60.0, "median_seconds": 11.0}, **change}), self.cfg())
            self.assertFalse(won)
            self.assertIn(word, why)

    def test_qa_alone_never_decides_a_win(self):
        old, new = self.summary(patch_tasks=0, tests_pass_pct=0), self.summary(patch_tasks=0, tests_pass_pct=0)
        won, why = ledger_eval.verdict(old, new, self.cfg())
        self.assertFalse(won)
        self.assertIn("No held-out patch examples", why)


class PatchScoringTests(SimpleTestCase):
    def test_no_patch_in_the_answer_is_refused_before_anything_runs(self):
        row = ledger_eval.score_patch({"files": ["app/calc.py"]}, "I cannot do that", 60)
        self.assertEqual((row["format_ok"], row["applies"]), (False, False))

    def test_a_protected_file_touch_is_refused_before_anything_runs(self):
        bad = "diff --git a/core/services/balance/b.py b/core/services/balance/b.py\n--- a/core/services/balance/b.py\n+++ b/core/services/balance/b.py\n@@ -0,0 +1 @@\n+b = 1\n"
        with patch.object(scoring, "extract_patch", return_value=bad):
            row = ledger_eval.score_patch({"files": ["core/services/balance/b.py"]}, "anything", 60)
        self.assertEqual((row["protected_touch"], row["applies"]), (True, False))


class RunNoTasksTests(SimpleTestCase):
    def test_no_held_out_tasks_says_how_to_build_them(self):
        out = ledger_eval.run(("a", "b"), [], "/tmp/does-not-matter", ask=None)
        self.assertEqual((out["status"], out["win"]), ("no_tasks", False))
        self.assertIn("build the dataset first", out["text"])
