"""
Unit tests for AI Platform, Autonomous Learning Engine, Dataset Engine, Model Lifecycle, and Benchmarks.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from core.models import AIBenchmarkReport
from core.services.ai.knowledge_engine import AIKnowledgeEngine
from core.services.ai.autonomous_learning_engine import AIAutonomousLearningEngine
from core.services.ai.dataset_engine import AIDatasetEngine
from core.services.ai.model_manager import AIModelManager
from core.services.ai.benchmark_engine import AIBenchmarkEngine


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
