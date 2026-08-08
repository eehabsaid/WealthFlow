"""
AI Autonomous Learning Engine.

Continuously observes application evolution (models, services, API routes, capabilities,
translations, schema changes) and updates the long-term Knowledge Base automatically.
"""

from __future__ import annotations

import logging
from typing import Any
from django.apps import apps
from core.services.ai.knowledge_engine import AIKnowledgeEngine
from core.services.ai.capability_registry import CapabilityRegistry
from core.services.ai.codebase_indexer import CodebaseIndexer

logger = logging.getLogger(__name__)


class AIAutonomousLearningEngine:
    """
    Autonomous engine that analyzes WealthFlow's codebase, models, services, and routes
    to continuously teach the AI about application evolution.
    """

    @classmethod
    def scan_and_learn_application_evolution(cls) -> dict[str, Any]:
        """
        Executes a complete scan of WealthFlow application components and updates Knowledge Base.
        """
        updated_entries = []

        # 1. Models & Database Schema Scan
        try:
            core_models = list(apps.get_app_config("core").get_models())
            model_names = [m.__name__ for m in core_models]
            model_entry = AIKnowledgeEngine.record_knowledge_entry(
                key="app_models_structure",
                title="WealthFlow Model Architecture",
                content=f"WealthFlow comprises {len(core_models)} core database models including: {', '.join(model_names[:10])}.",
                category="codebase_architecture",
                confidence=1.0,
                source="autonomous_learning",
            )
            updated_entries.append(model_entry.to_dict())
        except Exception as exc:
            logger.error("Error scanning models in autonomous learning: %s", exc)

        # 2. Capabilities & Financial Services Scan
        try:
            caps_res = CapabilityRegistry.get_capabilities()
            cap_count = caps_res.get("total_capabilities_registered", 0)
            cap_entry = AIKnowledgeEngine.record_knowledge_entry(
                key="app_capabilities_registry",
                title="Financial Capabilities & Analytics Services",
                content=f"WealthFlow has {cap_count} registered capabilities across Net Worth, Cash Flow, Certificates, Gold, Portfolio Optimization, and Risk Analysis.",
                category="business_rule",
                confidence=1.0,
                source="autonomous_learning",
            )
            updated_entries.append(cap_entry.to_dict())
        except Exception as exc:
            logger.error("Error scanning capabilities in autonomous learning: %s", exc)

        # 3. Codebase AST Structure Indexing
        try:
            ast_index = CodebaseIndexer.get_index(force_refresh=True)
            total_classes = ast_index.get("total_indexed_classes", 0)
            code_entry = AIKnowledgeEngine.record_knowledge_entry(
                key="app_codebase_ast_index",
                title="Application Service & AST Architecture",
                content=f"Indexed {total_classes} Python classes and services for real-time architectural questions.",
                category="codebase_architecture",
                confidence=1.0,
                source="autonomous_learning",
            )
            updated_entries.append(code_entry.to_dict())
        except Exception as exc:
            logger.error("Error scanning codebase AST in autonomous learning: %s", exc)

        # 4. Trigger Dataset Generator Pipeline
        try:
            from core.services.ai.dataset_engine import AIDatasetEngine
            AIDatasetEngine.generate_sft_datasets()
        except Exception as exc:
            logger.error("Error generating SFT datasets in autonomous learning: %s", exc)

        # 5. Regenerate System Knowledge Manifest & Markdown Files in ai_knowledge/
        try:
            from core.services.ai.knowledge_generator import KnowledgeGenerator
            KnowledgeGenerator.generate_all()
        except Exception as exc:
            logger.error("Error regenerating ai_knowledge files in autonomous learning: %s", exc)

        return {
            "ok": True,
            "updated_entries_count": len(updated_entries),
            "updated_entries": updated_entries,
        }
