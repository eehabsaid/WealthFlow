"""
Unit tests for AI Platform, Autonomous Learning Engine, Dataset Engine, Model Lifecycle, and Benchmarks.
"""

from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth.models import User
from core.models import AIBenchmarkReport, AIModelVersion, AppSettings
from core.services.ai.knowledge_engine import AIKnowledgeEngine
from core.services.ai.autonomous_learning_engine import AIAutonomousLearningEngine
from core.services.ai.dataset_engine import AIDatasetEngine
from core.services.ai.model_manager import AIModelManager
from core.services.ai.benchmark_engine import AIBenchmarkEngine
from core.services.ai.training_backends.ollama_backend import (
    OllamaTrainingBackend,
    _load_training_examples,
)


class AIPlatformTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_ai_user", password="password123")

    def test_knowledge_engine_record_and_context(self):
        entry = AIKnowledgeEngine.record_knowledge_entry(
            key="test_rule_1",
            title="Test Business Rule",
            content="Gold and EGP liquid assets are primary investment focus.",
            category="business_rule",
            confidence=0.9,
            source="unit_test",
        )
        self.assertEqual(entry.key, "test_rule_1")
        ctx = AIKnowledgeEngine.build_knowledge_context(self.user)
        self.assertIn("Test Business Rule", ctx)

    def test_autonomous_learning_engine_scan(self):
        res = AIAutonomousLearningEngine.scan_and_learn_application_evolution()
        self.assertTrue(res.get("ok"))
        self.assertGreaterEqual(res.get("updated_entries_count", 0), 1)

    def test_dataset_engine_generation_and_validation(self):
        AIKnowledgeEngine.record_knowledge_entry(
            key="test_ds_entry",
            title="Dataset Rule",
            content="Data content for dataset validation.",
        )
        stats = AIDatasetEngine.generate_sft_datasets()
        self.assertTrue(stats.get("ok"))
        self.assertGreaterEqual(stats.get("total_samples", 0), 1)

    def test_model_manager_and_benchmark_engine(self):
        active = AIModelManager.get_active_model_version()
        self.assertIsNotNone(active)
        self.assertTrue(active.is_active)

        report = AIBenchmarkEngine.evaluate_model_version(active, active)
        self.assertIsInstance(report, AIBenchmarkReport)
        self.assertGreaterEqual(report.overall_score, 0.0)

    def test_ai_platform_views(self):
        self.client.force_login(self.user)

        # Knowledge Endpoint
        res_k = self.client.get("/api/ai-platform/knowledge/")
        self.assertEqual(res_k.status_code, 200)

        # Dataset Endpoint
        res_d = self.client.get("/api/ai-platform/datasets/")
        self.assertEqual(res_d.status_code, 200)

        # Models Endpoint
        res_m = self.client.get("/api/ai-platform/models/")
        self.assertEqual(res_m.status_code, 200)

        # Benchmarks Endpoint
        res_b = self.client.get("/api/ai-platform/benchmarks/")
        self.assertEqual(res_b.status_code, 200)


class AIModelPromotionSyncTestCase(TestCase):
    """Covers the fix: promoting/rolling back a model version must actually
    update the 'ai_model' setting that live chat (ollama_provider) reads,
    and base_model defaults must follow whatever model is actually
    configured rather than a hardcoded tag that may not be pulled."""

    def setUp(self):
        AppSettings.set("ai_model", "qwen2.5:3b")

    def test_promote_model_version_syncs_live_chat_model(self):
        AIModelVersion.objects.create(
            version_name="wealthflow-v1", base_model="qwen2.5:3b",
            training_backend="ollama", dataset_version="v1.0",
            benchmark_score=90.0, is_active=True,
        )
        candidate = AIModelVersion.objects.create(
            version_name="wealthflow-v2", base_model="qwen2.5:3b",
            training_backend="ollama", dataset_version="v2.0",
            benchmark_score=95.0, is_active=False,
        )

        self.assertEqual(AppSettings.get("ai_model"), "qwen2.5:3b")
        promoted = AIModelManager.promote_model_version("wealthflow-v2")

        self.assertEqual(promoted.version_name, candidate.version_name)
        self.assertEqual(
            AppSettings.get("ai_model"), "wealthflow-v2",
            "Promoting a version must switch the live chat model, not just a DB flag.",
        )

    def test_rollback_also_syncs_live_chat_model(self):
        AIModelVersion.objects.create(
            version_name="wealthflow-v1", base_model="qwen2.5:3b",
            training_backend="ollama", dataset_version="v1.0",
            benchmark_score=90.0, is_active=False,
        )
        AIModelVersion.objects.create(
            version_name="wealthflow-v2", base_model="qwen2.5:3b",
            training_backend="ollama", dataset_version="v2.0",
            benchmark_score=95.0, is_active=True,
        )
        AppSettings.set("ai_model", "wealthflow-v2")

        AIModelManager.rollback_model_version("wealthflow-v1")

        self.assertEqual(AppSettings.get("ai_model"), "wealthflow-v1")

    def test_trigger_fine_tuning_defaults_to_configured_model_not_llama3(self):
        """Reproduces the reported bug: the base-model default must never be
        a hardcoded tag like llama3:latest that may not be pulled locally —
        it must fall back to whatever the user has actually confirmed works."""
        AppSettings.set("ai_model", "qwen2.5:3b")

        with patch("core.services.ai.model_manager.get_training_backend") as mock_get_backend:
            mock_backend = mock_get_backend.return_value
            mock_backend.train_model.return_value = {"ok": True, "model_version_name": "wealthflow-v2"}

            AIModelManager.trigger_fine_tuning(base_model=None)

            _, kwargs = mock_backend.train_model.call_args
            self.assertEqual(kwargs["base_model_name"], "qwen2.5:3b")
            self.assertNotEqual(kwargs["base_model_name"], "llama3:latest")

    def test_trigger_fine_tuning_respects_explicit_base_model_override(self):
        with patch("core.services.ai.model_manager.get_training_backend") as mock_get_backend:
            mock_backend = mock_get_backend.return_value
            mock_backend.train_model.return_value = {"ok": True, "model_version_name": "wealthflow-v2"}

            AIModelManager.trigger_fine_tuning(base_model="llama3.1:8b")

            _, kwargs = mock_backend.train_model.call_args
            self.assertEqual(kwargs["base_model_name"], "llama3.1:8b")


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
