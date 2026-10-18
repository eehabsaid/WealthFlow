"""
Unit tests for AI Platform endpoints and the Autonomous Learning Engine (the AIPlatformTestCase group).

Split out of the former monolithic test_ai_platform.py (200-line rule).
"""

from django.test import TestCase
from django.contrib.auth.models import User
from core.services.ai.knowledge_engine import AIKnowledgeEngine
from core.services.ai.autonomous_learning_engine import AIAutonomousLearningEngine
from core.tests.billing.test_support import grant_ai_workspace_access


class AIPlatformTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_ai_user", password="password123")
        grant_ai_workspace_access(self.user)

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

    def test_ai_platform_views(self):
        self.client.force_login(self.user)

        # Knowledge Endpoint
        res_k = self.client.get("/api/ai-platform/knowledge/")
        self.assertEqual(res_k.status_code, 200)

    def test_the_removed_training_endpoints_are_gone(self):
        self.client.force_login(self.user)
        for url in ("datasets", "models", "benchmarks"):
            self.assertEqual(self.client.get(f"/api/ai-platform/{url}/").status_code, 404, url)
