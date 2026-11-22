"""Training stage tests: command stages, dry stats and failure explanations."""


import os
import tempfile
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase

from ai.training.services import config, pipeline, train_stage
from ai.models import AISetting

from ai.training.tests.fakes import make_kept
from .train_stage_support import MODEL, StageBase


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
        with patch("ai.training.services.pipeline.ollama_stage.register") as register:
            text = self.call("--dry-run", "--min-traces", "3")
        register.assert_not_called()
        self.assertNotIn("questions from the live data", text)
        self.assertIn("Dry run: everything above is ready", text)

    def test_the_trained_model_gets_a_new_name_and_the_current_one_is_never_switched(self):
        make_kept(self.user, 3)
        with patch("ai.training.services.pipeline.ollama_stage.register", return_value=True) as register:
            text = self.call("--stages", "train", "--min-traces", "3")
        self.assertEqual(register.call_args.args[3], MODEL + "-agent2")
        self.assertEqual(register.call_args.args[2].endswith("mmproj-F16.gguf"), True)
        self.assertEqual(AISetting.get("ai_model", "", user=None), MODEL)
        self.assertIn(f"Your model in Settings ('{MODEL}') is unchanged", text)

    def test_no_model_name_in_settings_means_nothing_is_trained(self):
        AISetting.set("ai_model", "", user=None)
        make_kept(self.user, 3)
        self.assertIn("No model name is set", self.call("--stages", "train"))


class DryStatsTest(StageBase):
    def stats(self, tokenizer_module):
        from ai.training.tests.fakes import messages, write_jsonl
        path = os.path.join(tempfile.mkdtemp(), "t.jsonl")
        write_jsonl(path, [{"messages": messages(), "tools": []}, {"messages": messages(result="word " * 500), "tools": []}])
        lines = []
        with patch.dict("sys.modules", {"transformers": tokenizer_module}):
            train_stage.dry_stats(self.cfg.__class__(**{**self.cfg.as_dict(), "max_seq_length": 100}), path, lines.append)
        return "\n".join(lines)

    def test_counts_with_the_models_tokenizer(self):
        from types import SimpleNamespace
        from ai.training.tests.fakes import FakeTokenizer
        module = SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=lambda path: FakeTokenizer()))
        self.assertIn("1 of 2 examples fit 100 tokens (too long: 1", self.stats(module))

    def test_a_problem_is_reported_not_raised(self):
        from types import SimpleNamespace

        def boom(path):
            raise OSError("no tokenizer files")
        self.assertIn("Length check skipped: OSError", self.stats(SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=boom))))


class FailureExplainedTest(SimpleTestCase):
    def test_a_stopped_training_says_why_in_plain_words(self):
        text = train_stage.explain({"status": "training_failed", "gguf": "", "exit_code": 137})
        self.assertIn("NOT FINISHED", text)
        self.assertIn("exit code 137", text)
        self.assertIn("ran out of memory", text)
        self.assertEqual(train_stage.explain({"status": "trained", "gguf": "x"}), "")
