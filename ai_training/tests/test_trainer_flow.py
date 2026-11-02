"""The WSL trainer glue (train.py, export_gguf.py) with fake unsloth / trl: order of calls, settings passed, masks, outputs."""

from __future__ import annotations

import json
import os
import tempfile

from django.test import SimpleTestCase

from ai_training.trainer import export_gguf, train

from .fakes import FakeModel, FakeProcessor, FakeTokenizer, fake_deps, messages, write_jsonl

TOOLS = [{"type": "function", "function": {"name": "app_data_query"}}]


def entry(log, name):
    return next(e[1] for e in log if e[0] == name)


def make_cfg(folder, rows, **over):
    train_file = os.path.join(folder, "train.jsonl")
    write_jsonl(train_file, rows)
    base_model_dir = os.path.join(folder, "base_model")
    os.makedirs(base_model_dir, exist_ok=True)
    with open(os.path.join(base_model_dir, "config.json"), "w", encoding="utf-8") as fh:
        json.dump({"vision_config": {"model_type": "test"}}, fh)
    with open(os.path.join(base_model_dir, "preprocessor_config.json"), "w", encoding="utf-8") as fh:
        json.dump({"image_processor_type": "test"}, fh)
    cfg = {"base_model_dir": base_model_dir, "train_file": train_file, "out_dir": os.path.join(folder, "out"), "max_seq_length": 8192, "lora_rank": 16,
           "lora_alpha": 16, "epochs": 2, "learning_rate": 0.0002, "batch_size": 1, "grad_accum": 8, "enable_thinking": False, "gguf_quant": "q4_k_m"}
    return {**cfg, **over}


class TrainRunTest(SimpleTestCase):
    def test_full_flow_in_order_and_outputs(self):
        folder, log = tempfile.mkdtemp(), []
        cfg = make_cfg(folder, [{"messages": messages(), "tools": TOOLS}] * 3)
        summary = train.run(cfg, fake_deps(log), log=lambda line: None)
        steps = [entry[0] for entry in log]
        self.assertEqual(steps, ["load", "peft", "sft_config", "trainer", "masks", "train", "save_pretrained", "gguf"])
        load = entry(log, "load")
        self.assertEqual((load["model_name"], load["load_in_4bit"], load["full_finetuning"]), (cfg["base_model_dir"], True, False))
        peft = entry(log, "peft")
        self.assertEqual((peft["r"], peft["lora_alpha"], peft["finetune_vision_layers"], peft["finetune_language_layers"]), (16, 16, False, True))
        self.assertEqual(entry(log, "trainer"), 3)
        self.assertEqual([e for e in log if e[0] == "masks"][0][1:], ("<|im_start|>user\n", "<|im_start|>assistant\n"))
        self.assertEqual(entry(log, "gguf"), "q4_k_m")
        self.assertTrue(next(e[2] for e in log if e[0] == "gguf"))
        self.assertTrue(summary["gguf"].endswith("model.Q4_K_M.gguf"))
        self.assertTrue(summary["mmproj"].endswith("mmproj-F16.gguf"))
        self.assertTrue(os.path.isfile(os.path.join(summary["vision_assets"], "config.json")))
        self.assertTrue(os.path.isfile(os.path.join(summary["vision_assets"], "preprocessor_config.json")))
        self.assertEqual(summary["gguf_files"], [summary["gguf"]])
        self.assertEqual(json.load(open(os.path.join(cfg["out_dir"], "result.json")))["examples"], 3)
        self.assertEqual(json.load(open(os.path.join(cfg["out_dir"], "render_stats.json")))["kept"], 3)

    def test_the_length_setting_name_follows_the_trl_version(self):
        for key in ("max_length", "max_seq_length"):
            log = []
            train.run(make_cfg(tempfile.mkdtemp(), [{"messages": messages(), "tools": TOOLS}]), fake_deps(log, trl_key=key), log=lambda line: None)
            self.assertEqual(entry(log, "sft_config")["max_length" if key == "max_length" else "max_seq_length"], 8192)
            self.assertEqual(entry(log, "sft_config")["learning_rate"], 0.0002)

    def test_profile_checkpoint_directory_is_used_by_the_shared_trainer(self):
        folder, log = tempfile.mkdtemp(), []
        cfg = make_cfg(folder, [{"messages": messages(), "tools": TOOLS}], checkpoint_dir=os.path.join(folder, "profile-checkpoints"))
        train.run(cfg, fake_deps(log), log=lambda line: None)
        self.assertEqual(entry(log, "sft_config")["output_dir"], cfg["checkpoint_dir"])

    def test_examples_that_are_too_long_are_skipped_and_none_left_is_an_error(self):
        folder = tempfile.mkdtemp()
        rows = [{"messages": messages(), "tools": TOOLS}, {"messages": messages(result="word " * 500), "tools": TOOLS}]
        log = []
        train.run(make_cfg(folder, rows, max_seq_length=100), fake_deps(log), log=lambda line: None)
        self.assertEqual(entry(log, "trainer"), 1)
        with self.assertRaises(RuntimeError):
            train.run(make_cfg(tempfile.mkdtemp(), rows[1:], max_seq_length=100), fake_deps([]), log=lambda line: None)

    def test_the_processor_is_reduced_to_its_tokenizer(self):
        tok = FakeTokenizer()
        self.assertIs(train.text_tokenizer(type("P", (), {"tokenizer": tok})()), tok)
        self.assertIs(train.text_tokenizer(tok), tok)


class ExportTest(SimpleTestCase):
    def test_a_vision_export_without_an_mmproj_fails_explicitly(self):
        class NoProjector(FakeModel):
            def save_pretrained_gguf(self, path, processor, quantization_method):
                os.makedirs(path, exist_ok=True)
                open(os.path.join(path, "model.Q4_K_M.gguf"), "wb").write(b"model")

        cfg = make_cfg(tempfile.mkdtemp(), [])
        with self.assertRaisesRegex(RuntimeError, "vision projector"):
            export_gguf.save_all(NoProjector([]), FakeProcessor(FakeTokenizer()), cfg["out_dir"], "q4_k_m", cfg["base_model_dir"])

    def test_a_text_only_base_config_is_rejected_for_this_vision_model(self):
        cfg = make_cfg(tempfile.mkdtemp(), [])
        with open(os.path.join(cfg["base_model_dir"], "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"model_type": "text_only"}, fh)
        with self.assertRaisesRegex(RuntimeError, "no vision_config"):
            export_gguf.save_all(FakeModel([]), FakeProcessor(FakeTokenizer()), cfg["out_dir"], "q4_k_m", cfg["base_model_dir"])

    def test_no_model_file_is_an_error(self):
        class Empty(FakeModel):
            def save_pretrained_gguf(self, path, tokenizer, quantization_method):
                os.makedirs(path, exist_ok=True)

        with self.assertRaises(RuntimeError):
            cfg = make_cfg(tempfile.mkdtemp(), [])
            export_gguf.save_all(Empty([]), FakeProcessor(FakeTokenizer()), cfg["out_dir"], "q4_k_m", cfg["base_model_dir"])
