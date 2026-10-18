"""
Unit tests for the AI Platform endpoints: reading is open to AI-plan users, writing the knowledge base is sysadmin-only.

Split out of the former monolithic test_ai_platform.py (200-line rule).
"""

from django.test import TestCase
from django.contrib.auth.models import User
from core.services.ai.knowledge_engine import AIKnowledgeEngine
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

    def test_ai_platform_views(self):
        self.client.force_login(self.user)

        # Knowledge Endpoint
        res_k = self.client.get("/api/ai-platform/knowledge/")
        self.assertEqual(res_k.status_code, 200)

    def test_the_removed_training_endpoints_are_gone(self):
        self.client.force_login(self.user)
        for url in ("datasets", "models", "benchmarks"):
            self.assertEqual(self.client.get(f"/api/ai-platform/{url}/").status_code, 404, url)

    def test_everyone_can_read_but_only_a_sysadmin_can_write_the_knowledge_base(self):
        import json

        from core.authentication.services import AuthWorkflowService
        from core.models import AIKnowledgeEntry

        entry = AIKnowledgeEntry.objects.create(key="rule_x", title="Rule X", content="Original", category="business_rule")
        body = json.dumps({"key": "rule_y", "title": "Rule Y", "content": "New rule"})
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/ai-platform/knowledge/").status_code, 200)
        self.assertEqual(self.client.post("/api/ai-platform/knowledge/", data=body, content_type="application/json").status_code, 403)
        self.assertEqual(self.client.patch(f"/api/ai-platform/knowledge/{entry.id}/", data=json.dumps({"content": "Hacked"}), content_type="application/json").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/ai-platform/knowledge/{entry.id}/").status_code, 403)
        entry.refresh_from_db()
        self.assertEqual(entry.content, "Original")
        self.assertFalse(AIKnowledgeEntry.objects.filter(key="rule_y").exists())

        admin = User.objects.create_user(username="kb_admin", password="password123")
        profile = AuthWorkflowService.get_profile(admin)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        grant_ai_workspace_access(admin)
        self.client.force_login(admin)
        self.assertEqual(self.client.post("/api/ai-platform/knowledge/", data=body, content_type="application/json").status_code, 201)
        self.assertEqual(AIKnowledgeEntry.objects.get(key="rule_y").source, "user_manual")
        self.assertEqual(self.client.patch(f"/api/ai-platform/knowledge/{entry.id}/", data=json.dumps({"content": "Edited"}), content_type="application/json").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/ai-platform/knowledge/{entry.id}/").status_code, 200)

    def test_a_post_without_an_entry_no_longer_runs_a_scan(self):
        from core.authentication.services import AuthWorkflowService
        from core.models import AIKnowledgeEntry

        admin = User.objects.create_user(username="kb_admin2", password="password123")
        profile = AuthWorkflowService.get_profile(admin)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        grant_ai_workspace_access(admin)
        self.client.force_login(admin)
        before = AIKnowledgeEntry.objects.count()
        res = self.client.post("/api/ai-platform/knowledge/", data='{"action": "scan"}', content_type="application/json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(AIKnowledgeEntry.objects.count(), before)
