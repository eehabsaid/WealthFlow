"""The model test (M3), part 1: fresh test questions, the verdict rules and the Ollama controls."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from unittest.mock import patch

from ai_training.services import eval_report, generator, ollama_ctl, testset
from ai_training.services.case import norm_text
from ai_training.tests.eval_support import Base, add_expenses


class TestSetTest(Base):
    def test_questions_are_new_kinds_from_the_users_own_rows(self):
        add_expenses(self.user, ["10.00", "20.00", "30.00", "40.00"])
        cases = {c.key: c for c in testset.live_cases(self.user, 1)}
        self.assertTrue(all(k.startswith("eval:") for k in cases))
        self.assertFalse(set(cases) & {c.key for c in generator.generate(self.user)})
        self.assertEqual(cases["eval:Expense:max_per_currency:amount"].expected["values"], ["50.00"])   # the other user's 99.00 never counts
        self.assertEqual(cases["eval:Expense:min_per_currency:amount"].expected["values"], ["10.00"])
        last5 = cases["eval:Expense:last5:amount:date"]
        self.assertEqual(sorted(last5.expected["values"]), ["10.00", "20.00", "30.00", "40.00", "50.00"])
        self.assertIn("last 5", last5.question)

    def test_all_zero_answers_and_ties_at_the_cut_off_are_skipped(self):
        keys = {c.key for c in testset.live_cases(self.user, 1)}
        self.assertFalse(any(":avg:" in k and k.startswith("eval:Company") for k in keys))   # everything is 0.00 there
        add_expenses(self.user, ["10.00", "20.00", "30.00", "40.00"])
        self.assertIn("eval:Expense:last5:amount:date", {c.key for c in testset.live_cases(self.user, 1)})
        from core.models import Expense
        newest = list(Expense.objects.filter(owner=self.user).order_by("-date", "-pk"))
        extra = newest[-1]
        extra.pk, extra.date = None, newest[4].date
        extra.save()
        self.assertFalse(any("last5" in c.key for c in testset.live_cases(self.user, 1)))

    def test_every_language_is_asked_and_no_test_wording_is_a_training_question(self):
        add_expenses(self.user, ["10.00", "20.00", "30.00", "40.00"])
        test = testset.live_cases(self.user, 1)
        self.assertEqual({c.meta["lang"] for c in test}, {"en", "ar", "fr", "de"})
        train = {norm_text(c.question) for c in generator.generate(self.user)}
        self.assertFalse(train & {norm_text(c.question) for c in test})
        blocked = {norm_text(c.question) for c in test}
        self.assertFalse(blocked & {norm_text(c.question) for c in generator.generate(self.user, blocked=blocked)})

    def test_the_test_is_frozen_in_a_file_and_figures_are_recomputed(self):
        add_expenses(self.user, ["10.00", "20.00", "30.00", "40.00"])
        first, retired = testset.build(self.user, out_dir=self.out, per_category=3, seed=5)
        self.assertTrue(os.path.exists(os.path.join(self.out, testset.FILE)) and not retired)
        add_expenses(self.user, ["5.00"])                      # data changes after the freeze
        again, retired = testset.build(self.user, out_dir=self.out, per_category=3, seed=99)   # other seed: the file still wins
        self.assertEqual({c.key for c in again} | set(retired), {c.key for c in first})   # same frozen questions, none added
        mx = {c.key: c for c in again}.get("eval:Expense:max_per_currency:amount")
        if mx:
            self.assertEqual(mx.expected["values"], ["50.00"])

    def test_questions_are_spread_over_categories_and_languages(self):
        add_expenses(self.user, ["10.00", "20.00", "30.00", "40.00"])
        picked = testset.pick(testset.live_cases(self.user, 1), 4, 1)
        for cat in {c.meta["category"] for c in picked}:
            self.assertLessEqual(len([c for c in picked if c.meta["category"] == cat]), 4)
        self.assertGreaterEqual(len({c.meta["lang"] for c in picked}), 3)


class ReportTest(Base):
    def side(self, rate, median_s, n=20):
        return {"questions": n, "passed": 0, "rate": rate, "median_s": median_s, "mean_s": median_s, "reasons": {}}

    def test_verdict_rules(self):
        v = lambda old, new: eval_report.verdict(old, new, 5, 20)[0]
        self.assertEqual(v(self.side(50, 10), self.side(60, 11)), "NEW MODEL WINS")
        self.assertEqual(v(self.side(50, 10), self.side(60, 13)), "NEW MODEL IS MORE CORRECT BUT TOO SLOW")
        self.assertEqual(v(self.side(60, 10), self.side(50, 5)), "OLD MODEL IS BETTER")
        self.assertEqual(v(self.side(50, 10), self.side(53, 5)), "NO REAL DIFFERENCE")
        self.assertEqual(v(self.side(50, 10, n=4), self.side(90, 5, n=4)), "NOT ENOUGH QUESTIONS")

    def test_stats_use_the_counted_questions_only(self):
        rows = [{"passed": True, "seconds": 2.0, "reasons": []}, {"passed": False, "seconds": 10.0, "reasons": ["wrong_or_missing_figure:5"]},
                {"passed": True, "seconds": 4.0, "reasons": []}]
        s = eval_report.stats(rows)
        self.assertEqual((s["passed"], s["rate"], s["median_s"], s["reasons"]), (2, 66.7, 4.0, {"wrong_or_missing_figure": 1}))


class OllamaCtlTest(Base):
    def test_installed_reads_the_model_list_and_none_when_ollama_is_down(self):
        class Res:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return json.dumps({"models": [{"name": "a:1"}, {"model": "b"}]}).encode()
        with patch("ai_training.services.ollama_ctl.urllib.request.urlopen", return_value=Res()):
            self.assertEqual(ollama_ctl.installed("http://x"), {"a:1", "b:latest"})
        with patch("ai_training.services.ollama_ctl.urllib.request.urlopen", side_effect=OSError):
            self.assertIsNone(ollama_ctl.installed("http://x"))

    def test_restart_ends_ollama_and_starts_it_again_with_the_models_folder(self):
        fake_os = SimpleNamespace(name="nt", environ={})
        with patch.object(ollama_ctl, "os", fake_os), patch.object(ollama_ctl.subprocess, "run") as run, patch.object(ollama_ctl.subprocess, "Popen") as popen, \
                patch.object(ollama_ctl.time, "sleep"), patch.object(ollama_ctl, "wait_ready", return_value=True):
            self.assertTrue(ollama_ctl.restart(r"D:\ollama\models", "http://x", print))
        self.assertEqual([c.args[0][-1] for c in run.call_args_list], ["ollama app.exe", "ollama.exe"])
        self.assertEqual(popen.call_args.args[0], ["ollama", "serve"])
        self.assertEqual(popen.call_args.kwargs["env"]["OLLAMA_MODELS"], r"D:\ollama\models")

    def test_restart_is_refused_off_windows_and_when_starting_fails(self):
        self.assertFalse(ollama_ctl.restart("", "http://x", print))
        with patch.object(ollama_ctl, "os", SimpleNamespace(name="nt", environ={})), patch.object(ollama_ctl.subprocess, "run", side_effect=OSError("no")), \
                patch.object(ollama_ctl.time, "sleep"):
            self.assertFalse(ollama_ctl.restart("", "http://x", print))
