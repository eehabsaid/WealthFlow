"""The two scripts around the batch (scripts/traj_run.py, scripts/traj_make_tasks.py) and the Ollama pre-check: options reach the batch, a dry run runs nothing, a missing
model or a silent Ollama stops before any task, and a task list is written only when it passes every check."""

import importlib
import json
import sys
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import patch

from ai.services.coding import ROOT
from ai.services.coding.training import loop_stage, traj_batch
from ai.tests.coding.traj_helper import PATCH_GOAL, QA_GOAL, SMALL, TaskRepo, TrajRepo

MODEL = "qwen-test:recovery"
QA = {"id": "T001", "kind": "qa", "template": "what_does", "goal": QA_GOAL, "file": "app/calc.py", "symbol": "add", "line": 1, "why": ""}
PATCH = {"id": "T002", "kind": "patch", "template": "hints", "goal": PATCH_GOAL, "file": "app/calc.py", "symbol": "add", "line": 1, "why": ""}


def load_script(name):
    path = str(ROOT / "scripts")
    sys.path.insert(0, path)
    try:
        return importlib.import_module(name)
    finally:
        sys.path.remove(path)


class OllamaCheckTests(TrajRepo):
    def answer(self, names):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, *a):
                return json.dumps({"models": [{"name": n} for n in names]}).encode()

        return patch("urllib.request.urlopen", lambda *a, **k: Response())

    def test_a_missing_model_or_a_silent_ollama_is_reported_in_one_sentence(self):
        with self.answer([MODEL, "other:latest"]):
            self.assertEqual(traj_batch.preflight(MODEL, "http://x"), "")
        with self.answer([MODEL + ":latest"]):
            self.assertEqual(traj_batch.preflight(MODEL, "http://x"), "")
        with self.answer(["other:latest"]):
            self.assertIn("is not installed in Ollama", traj_batch.preflight(MODEL, "http://x"))
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            self.assertIn("does not answer", traj_batch.preflight(MODEL, "http://x"))


class ContextLineTests(TrajRepo):
    def test_the_usable_context_of_the_agent_is_told_in_one_line(self):
        line = traj_batch.context_line({"context_window": 150000, "reserve_tokens": 140000})
        self.assertIn("10,000 of 150,000 tokens usable per task (reserve 140,000)", line)
        self.assertIn("0 of 8,000", traj_batch.context_line({"context_window": 8000, "reserve_tokens": 9000}))


class ScriptTests(TrajRepo):
    def setUp(self):
        super().setUp()
        self.run_mod, self.out = load_script("traj_run"), []
        self.model = loop_stage.names(MODEL)[0]   # the model the loop evaluation compares against (agent_loop_training.json), not whatever Settings says
        self.work = tempfile.mkdtemp()
        for target, name, value in [(self.run_mod.AISetting, "get", lambda *a, **k: MODEL), (self.run_mod.traj_batch, "prepare", lambda *a, **k: [QA, PATCH]),
                                    (self.run_mod.traj_batch, "preflight", lambda *a, **k: ""), (self.run_mod, "print", lambda *a, **k: self.out.append(" ".join(map(str, a))))]:
            patcher = patch.object(target, name, value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch("ai.training.services.ollama_ctl.base_url", return_value="http://127.0.0.1:11434")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_dry_run_lists_what_would_run_with_the_comparison_model_and_runs_nothing(self):
        with patch.object(self.run_mod.traj_batch, "run", side_effect=AssertionError("a dry run must not run")):
            self.assertEqual(self.run_mod.main(["--dry-run", "--work", self.work, "--count", "1"]), 0)
        text = "\n".join(self.out)
        self.assertIn(f"Model: {self.model}   tasks to run: 1 of 2", text)
        self.assertIn("tokens usable per task", text)
        self.assertIn(QA_GOAL, text)
        self.assertNotIn(PATCH_GOAL, text)

    def test_a_real_run_passes_the_options_on_and_a_failed_preflight_stops_before_any_task(self):
        seen = {}
        with patch.object(self.run_mod.traj_batch, "run", lambda *a, **k: seen.update(args=a, kwargs=k) or {"text": "finished"}):
            self.assertEqual(self.run_mod.main(["--work", self.work, "--only", "T002", "--redo", "--timeout", "77"]), 0)
            self.assertEqual((seen["args"][3], seen["kwargs"]["only"], seen["kwargs"]["redo"], seen["kwargs"]["timeout"]), (self.model, {"T002"}, True, 77))
            with patch.object(self.run_mod.traj_batch, "preflight", lambda *a, **k: "Ollama does not answer"):
                seen.clear()
                self.assertEqual(self.run_mod.main(["--work", self.work]), 1)
                self.assertEqual(seen, {})

    def test_only_takes_ids_as_separate_words_or_comma_separated_because_powershell_splits_T001_comma_T002_into_two_words(self):
        seen = {}
        with patch.object(self.run_mod.traj_batch, "run", lambda *a, **k: seen.update(kwargs=k) or {"text": "finished"}):
            for words in (["T001", "T002"], ["T001,T002"], ["T001,", "T002"]):
                seen.clear()
                self.assertEqual(self.run_mod.main(["--work", self.work, "--only", *words, "--redo"]), 0)
                self.assertEqual((seen["kwargs"]["only"], seen["kwargs"]["redo"]), ({"T001", "T002"}, True), words)


class GeneratorScriptTests(TaskRepo):
    def test_the_generator_writes_a_list_only_when_it_passes_every_check_and_check_never_writes(self):
        mod, out = load_script("traj_make_tasks"), Path(tempfile.mkdtemp()) / "list.json"
        with patch.object(mod, "Project", lambda root: self.project), patch.object(mod, "print", lambda *a, **k: None, create=True):
            self.assertEqual(mod.main(["--out", str(out), "--check"]), 1, "there is no list to check yet")
            self.assertFalse(out.exists())
            self.assertEqual(mod.main(["--out", str(out)]), 1, "this tiny project cannot fill the real 60 + 40")
            self.assertFalse(out.exists(), "a list that fails the checks is never written")
            with patch.object(mod.traj_tasks, "QUOTAS", SMALL):
                self.assertEqual(mod.main(["--out", str(out)]), 0)
                tasks = json.loads(out.read_text(encoding="utf-8"))
                self.assertEqual([t["kind"] for t in tasks], ["qa", "qa", "patch", "qa", "patch"])
                self.assertEqual(mod.main(["--out", str(out), "--check"]), 0)
                (self.root / tasks[0]["file"]).unlink()
                self.assertEqual(mod.main(["--out", str(out), "--check"]), 1, "the list is checked against the files as they are now")
                self.assertEqual(json.loads(out.read_text(encoding="utf-8")), tasks, "--check never rewrites the list")
