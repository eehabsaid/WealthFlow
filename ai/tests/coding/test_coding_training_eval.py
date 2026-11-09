"""Phase 3 of the coding agent: patch scoring by real test runs, held-out evaluation, and the coding-only training gate."""

import os
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase

from ai.services.coding.training import evaluate, history, scoring, settings, stage

from ai.tests.coding.repo_helper import Repo

DIFF_HEADER = "diff --git a/core/app.py b/core/app.py"


class ScoringTests(Repo):
    def test_patch_extraction(self):
        diff = f"{DIFF_HEADER}\n--- a/core/app.py\n+++ b/core/app.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n"
        self.assertTrue(scoring.extract_patch(f"Here:\n```diff\n{diff}```\nDone").startswith("diff --git"))
        self.assertTrue(scoring.extract_patch(diff).startswith("diff --git"))
        self.assertEqual(scoring.extract_patch("I cannot do that"), "")
        self.assertEqual(history.patch_files(diff), ["core/app.py"])

    def test_scores_come_from_applying_the_patch_and_running_the_real_tests(self):
        ex = self.example()
        with patch.object(scoring, "_run", return_value=True) as run:
            good = scoring.score(ex, "```diff\n" + ex["diff"] + "```", 60, True)
            self.assertEqual((good["applies"], good["correct"], good["regression"]), (True, True, False))
            self.assertEqual(run.call_args_list[0].args[1], ["core.tests.test_app"])   # the change's own tests decide
            bad = scoring.score(ex, "```diff\n" + ex["diff"].replace("x = 1", "x = 99") + "```", 60, True)
            self.assertEqual((bad["applies"], bad["correct"]), (False, False))
            self.assertFalse(scoring.score(ex, "no patch here", 60, True)["format_ok"])

    def test_a_patch_that_fails_the_tests_or_breaks_the_area_is_counted(self):
        ex = self.example()
        with patch.object(scoring, "_run", return_value=False):
            self.assertEqual(scoring.score(ex, ex["diff"], 60, True)["correct"], False)
        with patch.object(scoring, "_run", side_effect=[True, False]), patch.object(scoring, "area_labels", return_value=["core.tests.x"]):
            row = scoring.score(ex, ex["diff"], 60, True)
            self.assertEqual((row["correct"], row["regression"]), (True, True))
        with patch.object(scoring, "_run", side_effect=[True, False]), patch.object(scoring, "area_labels", return_value=["core.tests.x"]):
            self.assertFalse(scoring.score(ex, ex["diff"], 60, False)["regression"])   # the area was already failing before: not blamed

    def test_touching_a_protected_file_is_refused_before_anything_runs(self):
        bad = "diff --git a/core/services/balance/b.py b/core/services/balance/b.py\n--- a/core/services/balance/b.py\n+++ b/core/services/balance/b.py\n@@ -0,0 +1 @@\n+b = 1\n"
        with patch.object(scoring, "_run") as run:
            row = scoring.score(self.example(), bad, 60, True)
        self.assertEqual((row["protected_touch"], row["correct"]), (True, False))
        run.assert_not_called()


class EvaluateTests(Repo):
    def cfg(self, **over):
        return {**settings(), **over}

    def test_verdict_needs_a_clear_win_and_no_new_problems(self):
        old = {"correct_pct": 40.0, "regressions": 1, "protected_touches": 0, "median_seconds": 10.0}
        win = {**old, "correct_pct": 60.0, "median_seconds": 11.0}
        self.assertTrue(evaluate.verdict(old, win, self.cfg())[0])
        for change, word in (({"correct_pct": 42.0}, "points"), ({"regressions": 2}, "regressions"), ({"protected_touches": 1}, "protected"), ({"median_seconds": 30.0}, "slower")):
            won, why = evaluate.verdict(old, {**win, **change}, self.cfg())
            self.assertFalse(won)
            self.assertIn(word, why)

    def test_both_models_are_scored_on_the_same_tasks_and_a_report_is_written(self):
        ex = self.example()
        answers = {"old-model": "I cannot do that", "new-model": ex["diff"]}
        ask = lambda model, messages, timeout: (answers[model], 2.0)  # noqa: E731
        out_dir, restarted = tempfile.mkdtemp(), []
        with patch.object(scoring, "_run", return_value=True), patch.object(scoring, "baseline_ok", return_value=True):
            out = evaluate.run(("old-model", "new-model"), [ex], out_dir, ask, lambda _: None, restarted.append)
        self.assertEqual((out["status"], out["win"], restarted), ("done", True, ["old-model", "new-model"]))
        self.assertEqual([r["correct"] for r in out["results"]], [0, 1])
        self.assertTrue(os.path.isfile(os.path.join(out_dir, "coding_eval_report.txt")))
        self.assertIn("Nothing was switched", out["text"])

    def test_a_model_that_does_not_answer_scores_zero_instead_of_stopping_the_run(self):
        def ask(model, messages, timeout):
            raise OSError("down")
        with patch.object(scoring, "baseline_ok", return_value=True):
            out = evaluate.run(("a", "b"), [self.example()], tempfile.mkdtemp(), ask, lambda _: None)
        self.assertEqual((out["results"][0]["correct"], out["win"]), (0, False))

    def test_no_held_out_tasks_says_how_to_build_them(self):
        out = evaluate.run(("a", "b"), [], tempfile.mkdtemp(), None)
        self.assertEqual((out["status"], out["win"]), ("no_tasks", False))


class TrainGateTests(SimpleTestCase):
    def test_new_model_name_is_the_original_plus_the_coding_suffix_and_never_an_old_name(self):
        cfg = stage.train_config()
        original, new = stage.names("qwen3.8:27b-150k-agent", cfg)
        self.assertTrue(new.endswith(settings()["model_suffix"]))
        self.assertNotEqual(new, "qwen3.8:27b-150k-agent")
        self.assertEqual(stage.names(original, cfg)[0], original)

    def test_too_few_verified_examples_blocks_training_before_anything_starts(self):
        path = os.path.join(tempfile.mkdtemp(), "t.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"messages": []}\n')
        logged = []
        with patch("ai.training.services.wsl.stream") as stream:
            out = stage.run(path, "qwen3.8:27b-150k", log=logged.append)
        self.assertEqual(out["status"], "blocked")
        stream.assert_not_called()
        self.assertTrue(any("verified coding examples" in line and "FIX" in line for line in logged))

    def test_line_counter_ignores_blank_lines_and_missing_files(self):
        self.assertEqual(stage.count_lines("/no/such/file"), 0)
