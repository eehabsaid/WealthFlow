"""
Unit tests for WealthFlow AI System Knowledge Foundation & Manifest Integration.
"""

from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.management import call_command

from core.services.ai.system_knowledge_engine import SystemKnowledgeEngine
from core.services.ai.knowledge_engine import AIKnowledgeEngine
from core.services.ai.context_builder_service import ContextBuilderService
from core.services.ai.orchestrator import AIContextOrchestrator
from core.services.ai.knowledge_generator import KnowledgeGenerator


class SystemKnowledgeEngineTestCase(TestCase):
    def setUp(self):
        SystemKnowledgeEngine.clear_cache()
        self.user = User.objects.create_user(username="knowledge_test_user", password="password123")

    def test_load_manifest(self):
        sections = SystemKnowledgeEngine.load_manifest()
        self.assertIsInstance(sections, list)
        self.assertGreaterEqual(len(sections), 8)

        section_ids = [s.get("id") for s in sections]
        expected_ids = [
            "application_architecture",
            "database_schema",
            "business_rules",
            "financial_rules",
            "investigation_protocols",
            "reasoning_guidelines",
            "response_guidelines",
            "ai_operating_manual",
        ]
        for eid in expected_ids:
            self.assertIn(eid, section_ids)

    def test_version_metadata(self):
        meta = SystemKnowledgeEngine.get_version_metadata()
        self.assertIn(meta.get("status"), ["active", "missing"])
        self.assertIn("knowledge_version", meta)

    def test_load_section_content(self):
        content = SystemKnowledgeEngine.load_section_content("01_application_architecture.md")
        self.assertIn("WealthFlow Application Architecture", content)

    def test_select_relevant_sections_by_query(self):
        salary_sections = SystemKnowledgeEngine.select_relevant_sections(query="salary deductions per diem")
        salary_ids = [s.get("id") for s in salary_sections]
        self.assertTrue(any(i in salary_ids for i in ["database_schema", "investigation_protocols", "business_rules"]))

        gold_sections = SystemKnowledgeEngine.select_relevant_sections(query="gold spot price karat")
        gold_ids = [s.get("id") for s in gold_sections]
        self.assertTrue(any(i in gold_ids for i in ["financial_rules", "business_rules", "database_schema"]))

    def test_build_system_knowledge_context(self):
        ctx = SystemKnowledgeEngine.build_system_knowledge_context(query="net worth calculation", token_limit=1000)
        self.assertIn("=== SYSTEM KNOWLEDGE & DOMAIN MANIFEST ===", ctx)

    def test_graceful_failure_missing_manifest(self):
        with patch.object(SystemKnowledgeEngine, "get_knowledge_dir") as mock_dir:
            from pathlib import Path
            mock_dir.return_value = Path("/nonexistent/directory/path")
            SystemKnowledgeEngine.clear_cache()

            # Should return empty data gracefully without raising exceptions
            manifest = SystemKnowledgeEngine.load_manifest(force_refresh=True)
            self.assertEqual(manifest, [])

            ctx = SystemKnowledgeEngine.build_system_knowledge_context(query="test", token_limit=500)
            self.assertEqual(ctx, "")

    def test_ai_knowledge_engine_integration(self):
        ctx = AIKnowledgeEngine.build_knowledge_context(user=self.user, query="portfolio analysis")
        self.assertIn("=== SYSTEM KNOWLEDGE & DOMAIN MANIFEST ===", ctx)

    def test_context_builder_service_system_prompt(self):
        service = ContextBuilderService()
        prompt = service.build_system_prompt(user=self.user, query="bank certificates interest")
        self.assertIn("SYSTEM KNOWLEDGE & DOMAIN MANIFEST", prompt)
        self.assertIn("CRITICAL DIRECTIVES:", prompt)

    def test_orchestrator_integration(self):
        res = AIContextOrchestrator.assemble_context(intent="business_analysis", user=self.user)
        self.assertIn("system_knowledge_manifest", res)
        self.assertIn("system_knowledge_manifest", res.get("_explanation_metadata", {}).get("context_sources", []))

    def test_knowledge_generator_and_management_command(self):
        res = KnowledgeGenerator.generate_all()
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["models_count"], 0)

        # Execute management command
        call_command("generate_ai_knowledge")
