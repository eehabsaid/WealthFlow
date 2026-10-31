"""The model test (M3), part 2: both models asked in turn, restart + warm-up, judging, report, and the model name in Settings always put back."""

from __future__ import annotations

import json
import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command

from ai_training.models import AgentTrace
from ai_training.services import eval_report, evaluate, export, inspect_file, ollama_ctl, runner
from ai_training.services.config import load
from ai_training.tests.eval_support import BEST, NEW, OLD, Base, add_expenses
from ai_training.tests.test_trace_pipeline import CTX, VIEW
from core.models import AppSettings


def plain_cfg():
    """The command reads config.json (your real model names); these tests use the generic test names instead."""
    return patch("ai_training.services.evaluate.load_config", side_effect=lambda: load(original_model="", best_model="", new_model=""))


class RunTest(Base):
    def setUp(self):
        super().setUp()
        add_expenses(self.user, ["10.00", "20.00", "30.00", "40.00"])

    def test_both_models_are_asked_in_turn_after_a_restart_and_the_setting_is_restored(self):
        result = self.run_eval(good_for=(OLD, NEW))
        self.assertEqual(result["status"], "done")
        models = [m for m, _, _ in self.asked]
        first_new = models.index(NEW)
        self.assertTrue(all(m == OLD for m in models[:first_new]) and all(m == NEW for m in models[first_new:]))
        self.assertEqual(models.count(OLD), models.count(NEW))                       # the same questions for both
        self.assertEqual({s for _, _, s in self.asked}, {"eval"})
        self.assertEqual(self.restart_mock.call_count, 2)                            # once before each model
        self.assertEqual(AppSettings.get("ai_model", "", user=None), OLD)            # restored
        self.assertFalse(os.path.exists(os.path.join(self.out, evaluate.MARKER)))
        self.assertEqual(AgentTrace.objects.count(), 0)                              # the test leaves no traces behind
        for name in ("eval_report.txt", "eval_results.json", "eval_runs.xlsx"):
            self.assertTrue(os.path.exists(os.path.join(self.out, name)), name)

    def test_warm_up_is_asked_but_not_counted(self):
        result = self.run_eval()
        per_model = len(json.load(open(result["paths"]["json"]))["models"][0]["rows"])
        self.assertEqual([m for m, _, _ in self.asked].count(OLD), per_model + 1)

    def test_a_wrong_model_loses_and_the_report_says_nothing_was_switched(self):
        result = self.run_eval(good_for=(OLD,))
        self.assertEqual(result["verdict"], "OLD MODEL IS BETTER")
        self.assertIn("Nothing was switched", result["report"])
        self.assertIn("wrong_or_missing_figure", result["report"])
        self.assertEqual(AppSettings.get("ai_model", "", user=None), OLD)

    def test_the_same_good_answers_are_no_real_difference(self):
        self.assertEqual(self.run_eval(good_for=(OLD, NEW))["verdict"], "NO REAL DIFFERENCE")

    def test_default_minimum_stops_a_decision_on_too_few_questions(self):
        self.assertEqual(self.run_eval(min_q=10_000)["verdict"], "NOT ENOUGH QUESTIONS")

    def test_a_crash_still_restores_the_model_name_and_cleans_up(self):
        with self.assertRaises(RuntimeError):
            self.run_eval(crash_on=NEW)
        self.assertEqual(AppSettings.get("ai_model", "", user=None), OLD)
        self.assertFalse(os.path.exists(os.path.join(self.out, evaluate.MARKER)))

    def test_a_killed_earlier_test_is_repaired_at_the_next_start(self):
        AppSettings.set("ai_model", NEW)
        with open(os.path.join(self.out, evaluate.MARKER), "w") as fh:
            json.dump({"ai_model": OLD}, fh)
        evaluate.recover(self.out, lambda line: None)
        self.assertEqual(AppSettings.get("ai_model", "", user=None), OLD)
        self.assertFalse(os.path.exists(os.path.join(self.out, evaluate.MARKER)))

    def test_a_missing_model_stops_the_test_with_a_plain_reason(self):
        result = self.run_eval(seen={OLD})
        self.assertEqual(result["status"], "blocked")
        self.assertIn(NEW, result["report"])
        self.assertEqual(AppSettings.get("ai_model", "", user=None), OLD)

    def test_if_ollama_cannot_be_restarted_the_models_are_unloaded_and_the_report_says_so(self):
        result = self.run_eval(restart=False)
        self.assertEqual(self.unload_mock.call_count, 4)                            # both models, before each of the two runs
        self.assertIn("NOT restarted", result["report"])

    def test_a_user_with_their_own_model_setting_blocks_the_test(self):
        from core.constants.ai_user_settings import USE_GENERAL_KEY
        AppSettings.set(USE_GENERAL_KEY, "false", user=self.user)
        AppSettings.set("ai_model", "my-own", user=self.user)
        result = self.run_eval()
        self.assertEqual(result["status"], "blocked")
        self.assertIn("own AI model setting", result["report"])
        self.assertEqual(AppSettings.get("ai_model", "", user=None), OLD)

    def test_provider_other_than_ollama_is_refused(self):
        AppSettings.set("ai_provider", "openai")
        self.assertEqual(self.run_eval()["status"], "not_ollama")

    def test_names_follow_the_suffix(self):
        self.assertEqual(evaluate.names(OLD, load(original_model="", best_model="", new_model="")), (OLD, BEST, NEW))
        self.assertEqual(evaluate.names(NEW, load(original_model="", best_model="", new_model="")), (OLD, BEST, NEW))
        self.assertEqual(evaluate.names(BEST, load(original_model="", best_model="", new_model="")), (OLD, BEST, NEW))

    def test_test_runs_never_reach_the_training_files(self):
        AgentTrace.objects.create(owner=self.user, source="eval", case_key="eval:x", question="q", verdict="kept", expected={"values": [1]})
        self.assertEqual(export.kept_traces(self.user), [])
        self.assertEqual(export.report(self.user)["questions"], 0)
        self.assertEqual(inspect_file.export_xlsx(os.path.join(self.out, "r.xlsx"), self.user), 0)


class CommandTest(Base):
    def test_dry_run_checks_questions_and_models_without_asking(self):
        out = StringIO()
        with patch.object(ollama_ctl, "installed", return_value={OLD, NEW}), patch("ai_training.services.runner.ask") as ask, plain_cfg():
            call_command("ai_training", "--user", "trace_user", "--stages", "evaluate", "--dry-run", "--out", self.out, stdout=out)
        self.assertIn("Frozen test questions:", out.getvalue())
        self.assertIn(f"[ok] Ollama has the original model '{OLD}'", out.getvalue())
        ask.assert_not_called()

    def test_the_command_prints_the_verdict(self):
        add_expenses(self.user, ["10.00", "20.00", "30.00", "40.00"])
        out = StringIO()
        with patch("ai_training.services.runner.ask", side_effect=self.scripted((OLD, NEW))), patch.object(eval_report, "MIN_QUESTIONS", 2), \
                patch.object(ollama_ctl, "restart", return_value=True), patch.object(ollama_ctl, "installed", return_value={OLD, NEW}), plain_cfg():
            call_command("ai_training", "--user", "trace_user", "--stages", "evaluate", "--out", self.out, stdout=out)
        self.assertIn("NO REAL DIFFERENCE", out.getvalue())
        self.assertIn("eval_report.txt", out.getvalue())


class AskPlumbingTest(Base):
    def test_a_test_question_goes_through_the_real_chat_endpoint_and_is_marked_as_a_test_run(self):
        provider = self.script(lambda n: "You have 3 expense records.")
        with patch(f"{VIEW}.get_active_ai_provider", return_value=provider), patch(f"{VIEW}.generation_pipeline.build_context", return_value=CTX):
            trace, problem = runner.ask(self.user, self.case, 1, source="eval")
        self.assertEqual((problem, trace.source), ("", "eval"))
        self.assertEqual(export.kept_traces(self.user), [])
