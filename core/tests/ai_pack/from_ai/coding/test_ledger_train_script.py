"""scripts/ledger_train.py: --mode loop picks the agent-loop pieces and the default mode keeps the QA + patch ones. Only the heavy parts (training, Ollama, the
evaluation itself) are replaced by recorders; the argument handling and the order of the stages are the real thing."""

import importlib
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from ai.services.coding import ROOT

HELD = [{"task_id": "a-qa", "task_kind": "qa", "goal": "q1", "answer": "x"}, {"task_id": "b-patch", "task_kind": "patch", "goal": "p1", "answer": ""},
        {"task_id": "c-qa", "task_kind": "qa", "goal": "q2", "answer": "y"}]


def load_script():
    path = str(ROOT / "scripts")
    sys.path.insert(0, path)
    try:
        return importlib.import_module("ledger_train")
    finally:
        sys.path.remove(path)


class ScriptModeTests(SimpleTestCase):
    def setUp(self):
        self.mod, self.calls = load_script(), []
        held = Path(tempfile.mkdtemp()) / "held.json"
        held.write_text(json.dumps(HELD), encoding="utf-8")
        self.built = {"train_file": "/x/train.jsonl", "held_out_file": str(held), "train": 3, "held_out": 1, "report": ""}

        def rec(name, result=None):
            return lambda *a, **k: self.calls.append((name, a, k)) or result

        for target, name, result in [(self.mod.ledger_review, "refresh", {"stats": {}}), (self.mod.ledger_review, "build_traj", self.built),
                                     (self.mod.ledger_review, "build_combined", self.built), (self.mod.loop_stage, "run", {"status": "trained"}),
                                     (self.mod.ledger_stage, "run", {"status": "trained"}), (self.mod.loop_eval, "run", {"text": "loop report"}),
                                     (self.mod.ledger_eval, "run", {"text": "single report"})]:
            patcher = patch.object(target, name, rec(f"{target.__name__.rsplit('.', 1)[1]}.{name}", result))
            patcher.start()
            self.addCleanup(patcher.stop)
        for target, name, value in [(self.mod.AISetting, "get", lambda *a, **k: "qwen3.8:27b-recovery"), (self.mod, "_restart", lambda cfg, url: "restart")]:
            patcher = patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch("ai.training.services.ollama_ctl.base_url", return_value="http://127.0.0.1:11434")
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_main(self, *argv):
        self.assertEqual(self.mod.main(list(argv)), 0)
        return [c[0] for c in self.calls]

    def call(self, name):
        return next(c for c in self.calls if c[0] == name)

    def test_the_default_mode_extracts_qa_and_patch_and_builds_the_combined_set(self):
        self.assertEqual(self.run_main("--stages", "extract"), ["ledger_review.refresh"] * 2)
        self.assertEqual([c[1][0] for c in self.calls], ["qa", "patch"])
        self.calls.clear()
        names = self.run_main("--stages", "build,train")
        self.assertEqual(names, ["ledger_review.build_combined", "ledger_stage.run"])
        self.assertEqual(self.call("ledger_stage.run")[1][0], "/x/train.jsonl")

    def test_loop_mode_extracts_trajectories_only_and_builds_the_loop_set(self):
        self.assertEqual(self.run_main("--mode", "loop", "--stages", "extract"), ["ledger_review.refresh"])
        self.assertEqual(self.calls[0][1][0], "traj")
        self.calls.clear()
        names = self.run_main("--mode", "loop", "--stages", "build,train", "--fresh", "--dry-run")
        self.assertEqual(names, ["ledger_review.build_traj", "loop_stage.run"])
        train = self.call("loop_stage.run")
        self.assertEqual((train[1][0], train[2]["fresh"], train[2]["dry_run"]), ("/x/train.jsonl", True, True))
        self.assertTrue(self.call("ledger_review.build_traj")[1][0].replace("\\", "/").endswith("/coding_agent_loop"))

    def test_loop_evaluate_runs_the_real_agent_loop_with_recovery_against_the_new_model(self):
        names = self.run_main("--mode", "loop", "--stages", "build,evaluate", "--max-eval-tasks", "2")
        self.assertEqual(names, ["ledger_review.build_traj", "loop_eval.run"])
        args, kwargs = self.call("loop_eval.run")[1:]
        self.assertEqual(args[0], ("qwen3.8:27b-recovery", "qwen3.8:27b-coding_agent_loop"))
        self.assertEqual([(t["task_id"], t["kind"]) for t in args[1]], [("a-qa", "qa"), ("b-patch", "patch")])
        self.assertEqual(kwargs["restart"], "restart")

    def test_loop_evaluate_without_a_limit_uses_the_config_cap(self):
        self.run_main("--mode", "loop", "--stages", "build,evaluate")
        self.assertEqual(len(self.call("loop_eval.run")[1][1]), 3, "three held-out tasks are below the eval_max_tasks of 12")

    def test_the_default_mode_evaluates_with_the_single_turn_evaluation(self):
        self.assertEqual(self.run_main("--stages", "build,evaluate"), ["ledger_review.build_combined", "ledger_eval.run"])

    def test_nothing_approved_skips_training_and_evaluation_in_both_modes(self):
        self.built.update(train=0, held_out=0)
        for mode in ("single", "loop"):
            self.calls.clear()
            self.run_main("--mode", mode, "--stages", "build,train,evaluate")
            self.assertEqual(len(self.calls), 1, mode)
