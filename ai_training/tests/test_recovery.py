from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase

from ai_training.services import config, recovery
from ai_training.trainer import render
from ai_training.tests.fakes import FakeTokenizer


class RecoveryProfileTest(SimpleTestCase):
    def test_profiles_are_isolated_and_the_legacy_config_remains_the_default(self):
        wealthflow = config.load()
        profile, recovered = recovery.load_profile()
        legacy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
        wealthflow_profile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "profiles", "wealthflow.json")
        with open(legacy_path, encoding="utf-8") as fh:
            legacy_json = json.load(fh)
        with open(wealthflow_profile_path, encoding="utf-8") as fh:
            profile_json = json.load(fh)
        self.assertEqual(legacy_json, profile_json)
        self.assertEqual(wealthflow.work_dir, legacy_json["work_dir"])
        self.assertEqual(recovered.model_suffix, "-recovery")
        self.assertEqual(recovered.new_model, "qwen3.8:27b-recovery")
        self.assertNotEqual(recovered.work_dir, wealthflow.work_dir)
        self.assertNotEqual(recovered.run_dir_override, "")
        self.assertNotEqual(recovered.checkpoint_dir_override, "")
        self.assertEqual(profile["dataset_format"], "qa_jsonl")

    def test_recovery_command_selects_the_profile_without_looking_up_a_user(self):
        with patch("ai_training.services.recovery.run", return_value={"report": "ok", "paths": {}}) as run:
            call_command("ai_training", "--profile", "recovery", "--stages", "validate")
        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs["stages"], "validate")

    def test_default_command_profile_is_still_wealthflow(self):
        from ai_training.management.commands.ai_training import Command

        parser = __import__("argparse").ArgumentParser()
        Command().add_arguments(parser)
        self.assertEqual(parser.parse_args([]).profile, "wealthflow")


class RecoveryDatasetTest(SimpleTestCase):
    def test_complete_dataset_validates_with_all_required_topics(self):
        profile, _ = recovery.load_profile()
        report = recovery.validate_dataset(profile, write_report=False)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["examples"], 35)
        self.assertEqual(set(report["topics"]), set(profile["required_topics"]))

    def test_export_produces_the_trainer_chat_jsonl_format(self):
        profile, _ = recovery.load_profile()
        folder = tempfile.mkdtemp()
        profile = {**profile, "exported_dataset_path": os.path.join(folder, "train.jsonl"), "reports_dir": folder}
        output, report = recovery.export_dataset(profile)
        texts, stats = render.render_file(output, FakeTokenizer(), 8192, False)
        self.assertEqual(report["examples"], 35)
        self.assertEqual(stats["kept"], 35)
        with open(output, encoding="utf-8") as fh:
            row = json.loads(fh.readline())
        self.assertEqual([message["role"] for message in row["messages"]], ["system", "user", "assistant"])
        self.assertIn("authorized", row["messages"][0]["content"])
        self.assertEqual(len(texts), 35)

    def test_invalid_or_duplicate_examples_are_rejected_and_reported(self):
        folder = tempfile.mkdtemp()
        dataset = os.path.join(folder, "questions.jsonl")
        with open(dataset, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"topic": "instruction", "question": "Repeated question?", "answer": "A sufficiently long answer for validation."}) + "\n")
            fh.write(json.dumps({"topic": "instruction", "question": "Repeated question?", "answer": ""}) + "\n")
        profile = {
            "dataset_path": dataset,
            "required_topics": ["instruction"],
            "minimum_examples": 1,
            "reports_dir": folder,
        }
        report = recovery.validate_dataset(profile)
        self.assertFalse(report["valid"])
        self.assertTrue(any("duplicate question" in error for error in report["errors"]))
        self.assertTrue(any("answer must contain" in error for error in report["errors"]))
        with self.assertRaisesRegex(ValueError, "INVALID"):
            recovery.export_dataset({**profile, "exported_dataset_path": os.path.join(folder, "out.jsonl")})

    def test_train_stage_validates_and_exports_when_called_directly(self):
        profile, cfg = recovery.load_profile()
        folder = tempfile.mkdtemp()
        profile.update({
            "reports_dir": folder,
            "exported_dataset_path": os.path.join(folder, "train.jsonl"),
        })
        with patch.object(recovery, "load_profile", return_value=(profile, cfg)), \
                patch.object(recovery.train_stage, "run_prepared", return_value={"status": "dry_run"}) as train:
            result = recovery.run(stages="train", dry_run=True, log=lambda _: None)
        train.assert_called_once()
        self.assertEqual(train.call_args.args[2], 35)
        self.assertEqual(train.call_args.args[3], profile["base_ollama_model"])
        self.assertTrue(os.path.isfile(profile["exported_dataset_path"]))
        self.assertEqual(result["training"]["status"], "dry_run")
