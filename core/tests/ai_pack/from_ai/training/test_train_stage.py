"""The training stage and the whole `ai_training` command with a fake WSL and a fake Ollama: order, blocking, dry run, resume, no auto-switch."""


import json
import os
import tempfile
from unittest.mock import patch


from ai.training.services import config, preflight, train_stage, wsl

from ai.training.tests.fakes import make_kept
from .train_stage_support import MODEL, StageBase


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

    def test_prepared_dataset_uses_profile_specific_run_export_and_checkpoint_paths(self):
        folder = tempfile.mkdtemp()
        source = os.path.join(folder, "prepared.jsonl")
        with open(source, "w", encoding="utf-8") as fh:
            fh.write('{"messages": []}\n')
        run_dir = os.path.join(folder, "run-recovery")
        out_dir = os.path.join(run_dir, "out")
        checkpoint_dir = os.path.join(out_dir, "checkpoints")
        cfg = config.load(
            base_model_dir=self.base,
            work_dir=os.path.join(folder, "work"),
            run_dir_override=run_dir,
            out_dir_override=out_dir,
            checkpoint_dir_override=checkpoint_dir,
            min_traces=3,
            min_free_gb=0,
        )
        with patch.object(preflight, "base_checks", return_value=[]), patch.object(preflight, "wsl_checks", return_value=[]), \
                patch.object(train_stage, "dry_stats") as stats:
            result = train_stage.run_prepared(cfg, source, 3, MODEL, dry_run=True, log=lambda _: None)
        self.assertEqual(result["status"], "dry_run")
        stats.assert_called_once()
        self.assertEqual(stats.call_args.args[:2], (cfg, os.path.join(run_dir, "train.jsonl")))
        run_config = json.load(open(os.path.join(run_dir, "run_config.json"), encoding="utf-8"))
        self.assertEqual(run_config["train_file"], wsl.to_wsl_path(os.path.join(run_dir, "train.jsonl")))
        self.assertEqual(run_config["out_dir"], wsl.to_wsl_path(out_dir))
        self.assertEqual(run_config["checkpoint_dir"], wsl.to_wsl_path(checkpoint_dir))

    def test_prepared_training_passes_the_verified_initial_agent_adapter_to_wsl(self):
        folder = tempfile.mkdtemp()
        source = os.path.join(folder, "prepared.jsonl")
        with open(source, "w", encoding="utf-8") as fh:
            fh.write('{"messages": []}\n')
        source_run = os.path.join(folder, "agent2-run")
        source_out = os.path.join(source_run, "out")
        adapter_dir = os.path.join(source_out, "adapter")
        os.makedirs(adapter_dir)
        with open(os.path.join(adapter_dir, "adapter_config.json"), "w", encoding="utf-8") as fh:
            json.dump({"peft_type": "LORA", "base_model_name_or_path": self.base, "r": 16}, fh)
        open(os.path.join(adapter_dir, "adapter_model.safetensors"), "wb").write(b"weights")
        with open(os.path.join(source_run, "run_config.json"), "w", encoding="utf-8") as fh:
            json.dump({"new_model": "agent2", "base_model_dir": self.base}, fh)
        with open(os.path.join(source_out, "result.json"), "w", encoding="utf-8") as fh:
            json.dump({"adapter": adapter_dir}, fh)
        run_dir = os.path.join(folder, "run-recovery")
        cfg = config.load(
            base_model_dir=self.base,
            work_dir=os.path.join(folder, "work"),
            run_dir_override=run_dir,
            min_traces=3,
            min_free_gb=0,
            initial_adapter_dir=adapter_dir,
            initial_adapter_model="agent2",
        )
        with patch.object(preflight, "base_checks", return_value=[]), patch.object(preflight, "wsl_checks", return_value=[]), \
                patch.object(train_stage, "dry_stats"):
            result = train_stage.run_prepared(cfg, source, 3, MODEL, dry_run=True, log=lambda _: None)
        self.assertEqual(result["status"], "dry_run")
        run_config = json.load(open(os.path.join(run_dir, "run_config.json"), encoding="utf-8"))
        self.assertEqual(run_config["initial_adapter_dir"], wsl.to_wsl_path(adapter_dir))
        self.assertEqual(run_config["initial_adapter_model"], "agent2")

    def test_a_finished_export_without_result_note_keeps_its_model_projector_and_vision_assets(self):
        out = os.path.join(train_stage.run_dir(self.cfg), "out")
        for sub, name, size in (("gguf_gguf", "M.Q4_K_M.gguf", 50), ("gguf_gguf", "M.BF16-mmproj.gguf", 90), ("adapter", "a.txt", 1)):
            os.makedirs(os.path.join(out, sub), exist_ok=True)
            open(os.path.join(out, sub, name), "w").write("x" * size)
        vision = os.path.join(out, "vision")
        os.makedirs(vision, exist_ok=True)
        json.dump({"vision_config": {"model_type": "test"}}, open(os.path.join(vision, "config.json"), "w"))
        open(os.path.join(vision, "preprocessor_config.json"), "w").write("{}")
        open(os.path.join(vision, "tokenizer.json"), "w").write("{}")
        self.assertTrue(train_stage.finished_model(self.cfg).endswith("M.Q4_K_M.gguf"))

    def test_full_run_prepares_then_trains_with_wsl_paths_and_returns_the_model_file(self):
        make_kept(self.user, 3)
        out, _ = self.go()
        self.assertEqual(out["status"], "trained")
        self.assertTrue(out["gguf"].endswith("m.gguf"))
        self.assertTrue(out["mmproj"].endswith("mmproj-F16.gguf"))
        self.assertTrue(out["vision_assets"].endswith("vision"))
        self.assertIn("setup_env.sh", self.streams[0])
        self.assertIn("-m ai.training.trainer.train --config", self.streams[1])
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
        with a, b, c, patch("ai.training.services.train_stage.subprocess.run", side_effect=lambda cmd, **kw: order.append(cmd) or type("R", (), {"returncode": 0})()), \
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
