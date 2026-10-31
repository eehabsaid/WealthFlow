"""The training stage and the whole `ai_training` command with a fake WSL and a fake Ollama: order, blocking, dry run, resume, no auto-switch."""

from __future__ import annotations

import json
import os
import tempfile
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from ai_training.services import config, pipeline, preflight, train_stage, wsl
from core.models import AppSettings
from core.tests.ai.investigation.support import make_user

from .fakes import make_kept

MODEL = "qwen3.8:27b-150k"


class StageBase(TestCase):
    def setUp(self):
        self.user = make_user("train_user", sysadmin=True)
        folder = tempfile.mkdtemp()
        self.base = os.path.join(folder, "model")
        os.makedirs(self.base)
        for name in ("config.json", "model-00001.safetensors"):
            open(os.path.join(self.base, name), "w").write("x")
        self.cfg = config.load(base_model_dir=self.base, work_dir=os.path.join(folder, "work"), min_free_gb=0, min_traces=3)
        self.streams = []
        AppSettings.set("ai_model", MODEL, user=None)

    def stream(self, cmd_log, fail_on=None, make_result=True):
        def fake(cfg, script, log):
            self.streams.append(script)
            log(f"running: {script[:40]}")
            if fail_on and fail_on in script:
                return 1
            if make_result and "trainer.train" in script:
                out = os.path.join(train_stage.run_dir(self.cfg), "out")
                os.makedirs(out, exist_ok=True)
                gguf = os.path.join(out, "gguf", "m.gguf")
                os.makedirs(os.path.dirname(gguf), exist_ok=True)
                open(gguf, "w").write("x")
                json.dump({"gguf": gguf}, open(os.path.join(out, "result.json"), "w"))
            return 0
        return fake

    def patches(self, **kw):
        ready = [preflight.Check("GPU inside WSL", True, "ok")]
        return (patch.object(preflight, "_ollama_has", return_value=True), patch.object(preflight, "wsl_checks", return_value=kw.get("wsl", ready)),
                patch.object(wsl, "stream", side_effect=self.stream(None, kw.get("fail_on"), kw.get("make_result", True))))


class TrainStageTest(StageBase):
    def go(self, **kw):
        a, b, c = self.patches(**kw)
        lines = []
        with a, b, c:
            out = train_stage.run(self.cfg, self.user, MODEL, dry_run=kw.get("dry_run", False), fresh=kw.get("fresh", False), log=lines.append)
        return out, "\n".join(lines)

    def test_too_few_traces_block_with_a_plain_reason_and_nothing_is_started(self):
        make_kept(self.user, 2)
        out, text = self.go()
        self.assertEqual(out["status"], "blocked")
        self.assertIn("[FIX] proven traces: 2 (need 3)", text)
        self.assertEqual(self.streams, [])

    def test_a_failed_wsl_check_blocks(self):
        make_kept(self.user, 3)
        out, text = self.go(wsl=[preflight.Check("GPU inside WSL", False, "none", "update the driver")])
        self.assertEqual(out["status"], "blocked")
        self.assertIn("update the driver", text)

    def test_dry_run_writes_the_data_file_but_starts_nothing(self):
        make_kept(self.user, 3)
        out, text = self.go(dry_run=True)
        self.assertEqual(out["status"], "dry_run")
        self.assertEqual(self.streams, [])
        self.assertEqual(len(open(os.path.join(train_stage.run_dir(self.cfg), "train.jsonl")).read().splitlines()), 3)
        self.assertIn("Dry run: everything above is ready", text)

    def test_a_finished_export_without_result_note_is_found_in_gguf_gguf(self):
        out = os.path.join(train_stage.run_dir(self.cfg), "out")
        for sub, name, size in (("gguf_gguf", "M.Q4_K_M.gguf", 50), ("gguf_gguf", "M.BF16-mmproj.gguf", 90), ("adapter", "a.txt", 1)):
            os.makedirs(os.path.join(out, sub), exist_ok=True)
            open(os.path.join(out, sub, name), "w").write("x" * size)
        self.assertTrue(train_stage.finished_model(self.cfg).endswith("M.Q4_K_M.gguf"))

    def test_full_run_prepares_then_trains_with_wsl_paths_and_returns_the_model_file(self):
        make_kept(self.user, 3)
        out, _ = self.go()
        self.assertEqual(out["status"], "trained")
        self.assertTrue(out["gguf"].endswith("m.gguf"))
        self.assertIn("setup_env.sh", self.streams[0])
        self.assertIn("-m ai_training.trainer.train --config", self.streams[1])
        wsl_cfg = json.load(open(os.path.join(train_stage.run_dir(self.cfg), "run_config.json")))
        self.assertEqual(wsl_cfg["base_model_dir"], wsl.to_wsl_path(self.base))
        self.assertTrue(wsl_cfg["train_file"].endswith("/train.jsonl"))
        self.assertEqual(wsl_cfg["max_seq_length"], 8192)

    def test_low_wsl_memory_is_fixed_by_the_real_run_and_only_by_it(self):
        make_kept(self.user, 3)
        low = [preflight.Check("WSL memory", False, "32 GB", "x")]
        fixed = [preflight.Check("WSL memory", True, "52 GB")]
        answers = iter([low, fixed])
        a, b, c = self.patches()
        with a, patch.object(preflight, "wsl_checks", side_effect=lambda cfg: next(answers)), c, \
                patch.object(preflight, "set_wsl_memory", return_value=True) as setter, patch.object(wsl, "shutdown") as shutdown:
            out = train_stage.run(self.cfg, self.user, MODEL, log=lambda line: None)
        setter.assert_called_once()
        shutdown.assert_called_once()
        self.assertEqual(out["status"], "trained")
        a, b, c = self.patches(wsl=low)
        with a, b, c, patch.object(preflight, "set_wsl_memory") as setter:
            train_stage.run(self.cfg, self.user, MODEL, dry_run=True, log=lambda line: None)
        setter.assert_not_called()

    def test_the_model_is_unloaded_from_the_gpu_before_training_starts(self):
        make_kept(self.user, 3)
        order = []
        a, b, c = self.patches()
        with a, b, c, patch("ai_training.services.train_stage.subprocess.run", side_effect=lambda cmd, **kw: order.append(cmd) or type("R", (), {"returncode": 0})()), \
                patch.object(wsl, "stream", side_effect=lambda cfg, script, log: order.append("wsl") or 1):
            train_stage.run(self.cfg, self.user, MODEL, log=lambda line: None)
        self.assertEqual(order[:2], [["ollama", "stop", MODEL], "wsl"])

    def test_a_finished_run_is_reused_unless_fresh(self):
        make_kept(self.user, 3)
        self.go()
        self.streams.clear()
        out, text = self.go()
        self.assertEqual((out["status"], self.streams), ("reused", []))
        self.assertEqual(self.go(fresh=True)[0]["status"], "trained")

    def test_each_failure_has_its_own_status(self):
        make_kept(self.user, 3)
        self.assertEqual(self.go(fail_on="setup_env")[0]["status"], "setup_failed")
        self.assertEqual(self.go(fail_on="trainer.train")[0]["status"], "training_failed")
        self.assertEqual(self.go(make_result=False)[0]["status"], "no_model_file")


class CommandStagesTest(StageBase):
    def call(self, *args):
        out = StringIO()
        a, b, c = self.patches()
        with a, b, c, patch.object(pipeline, "load_config", side_effect=lambda **kw: config.load(original_model="", new_model="", base_model_dir=self.base, work_dir=self.cfg.work_dir,
                                                                                               min_free_gb=0, **{k: v for k, v in kw.items() if v is not None})):
            call_command("ai_training", "--user", "train_user", "--out", tempfile.mkdtemp(), *args, stdout=out)
        return out.getvalue()

    def test_dry_run_asks_no_questions_and_registers_nothing(self):
        make_kept(self.user, 3)
        with patch("ai_training.services.pipeline.ollama_stage.register") as register:
            text = self.call("--dry-run", "--min-traces", "3")
        register.assert_not_called()
        self.assertNotIn("questions from the live data", text)
        self.assertIn("Dry run: everything above is ready", text)

    def test_the_trained_model_gets_a_new_name_and_the_current_one_is_never_switched(self):
        make_kept(self.user, 3)
        with patch("ai_training.services.pipeline.ollama_stage.register", return_value=True) as register:
            text = self.call("--stages", "train", "--min-traces", "3")
        self.assertEqual(register.call_args.args[2], MODEL + "-agent2")
        self.assertEqual(AppSettings.get("ai_model", "", user=None), MODEL)
        self.assertIn(f"Your model in Settings ('{MODEL}') is unchanged", text)

    def test_no_model_name_in_settings_means_nothing_is_trained(self):
        AppSettings.set("ai_model", "", user=None)
        make_kept(self.user, 3)
        self.assertIn("No model name is set", self.call("--stages", "train"))


class DryStatsTest(StageBase):
    def stats(self, tokenizer_module):
        from .fakes import messages, write_jsonl
        path = os.path.join(tempfile.mkdtemp(), "t.jsonl")
        write_jsonl(path, [{"messages": messages(), "tools": []}, {"messages": messages(result="word " * 500), "tools": []}])
        lines = []
        with patch.dict("sys.modules", {"transformers": tokenizer_module}):
            train_stage.dry_stats(self.cfg.__class__(**{**self.cfg.as_dict(), "max_seq_length": 100}), path, lines.append)
        return "\n".join(lines)

    def test_counts_with_the_models_tokenizer(self):
        from types import SimpleNamespace
        from .fakes import FakeTokenizer
        module = SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=lambda path: FakeTokenizer()))
        self.assertIn("1 of 2 examples fit 100 tokens (too long: 1", self.stats(module))

    def test_a_problem_is_reported_not_raised(self):
        from types import SimpleNamespace

        def boom(path):
            raise OSError("no tokenizer files")
        self.assertIn("Length check skipped: OSError", self.stats(SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=boom))))
