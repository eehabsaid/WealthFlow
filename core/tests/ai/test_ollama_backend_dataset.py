"""
Ollama training-backend dataset-usage tests
(OllamaBackendDatasetUsageTestCase group).

Split out of the former monolithic test_ai_platform.py (200-line rule).
"""

from unittest.mock import patch

from django.test import TestCase
from core.services.ai.training_backends.ollama_backend import (
    OllamaTrainingBackend,
    _load_training_examples,
)


class OllamaBackendDatasetUsageTestCase(TestCase):
    """Covers the fix: training must actually read and incorporate the
    generated SFT dataset into the Modelfile, instead of silently ignoring
    dataset_path and producing a plain system-prompt wrapper."""

    def test_load_training_examples_parses_valid_jsonl(self):
        content = (
            '{"instruction": "What is my net worth?", "context": "", '
            '"reasoning": "sum assets", "answer": "9,139,728.43 EGP"}\n'
            '{"instruction": "", "answer": "skip me, no instruction"}\n'
            "not even json\n"
            '{"instruction": "List my banks", "context": "Category: balance.", '
            '"answer": "CIB, NBE"}\n'
        )
        path = self._write_tmp(content)
        examples = _load_training_examples(path)

        self.assertEqual(len(examples), 2)
        self.assertEqual(examples[0]["user"], "What is my net worth?")
        self.assertEqual(examples[0]["assistant"], "9,139,728.43 EGP")
        self.assertIn("Category: balance.", examples[1]["user"])

    def test_load_training_examples_handles_missing_file(self):
        self.assertEqual(_load_training_examples("/no/such/file.jsonl"), [])
        self.assertEqual(_load_training_examples(""), [])

    def test_train_model_embeds_dataset_examples_in_modelfile(self):
        content = (
            '{"instruction": "What is my net worth?", "context": "", "answer": "9,139,728.43 EGP"}\n'
        )
        dataset_path = self._write_tmp(content)
        backend = OllamaTrainingBackend()

        captured_modelfile = {}

        def fake_run(cmd, **kwargs):
            if cmd[:2] == ["ollama", "--version"]:
                return _FakeResult(0)
            if cmd[:2] == ["ollama", "create"]:
                modelfile_path = cmd[-1]
                with open(modelfile_path, encoding="utf-8") as f:
                    captured_modelfile["content"] = f.read()
                return _FakeResult(0)
            return _FakeResult(1, stderr="unexpected command")

        with patch("core.services.ai.training_backends.ollama_backend.subprocess.run", side_effect=fake_run):
            result = backend.train_model(
                dataset_path=dataset_path,
                base_model_name="qwen2.5:3b",
                output_version_name="wealthflow-test",
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["training_examples_used"], 1)
        self.assertIn("FROM qwen2.5:3b", captured_modelfile["content"])
        self.assertIn("MESSAGE user", captured_modelfile["content"])
        self.assertIn("What is my net worth?", captured_modelfile["content"])
        self.assertIn("MESSAGE assistant", captured_modelfile["content"])
        self.assertIn("9,139,728.43 EGP", captured_modelfile["content"])

    def _write_tmp(self, content):
        import tempfile
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        self.addCleanup(lambda: __import__("os").remove(f.name))
        return f.name


class _FakeResult:
    def __init__(self, returncode, stderr=""):
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = ""
