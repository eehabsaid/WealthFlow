"""
WealthFlow AI System Knowledge Engine.

Loads, indexes, caches, and dynamically selects system knowledge sections
from the project-level `ai_knowledge/` directory based on user query intent.

Provides permanent structural understanding (architecture, schema, business rules,
financial calculations, investigation protocols, response standards) to AI system prompts
in a provider-independent, token-efficient manner.

FAIL-SAFE DESIGN:
If MANIFEST.json or markdown files are missing, unreadable, or invalid, the engine logs diagnostic
warnings and returns empty context gracefully without throwing runtime exceptions or halting AI execution.

Split (>200-line convention) into:
- manifest.py   — MANIFEST.json / section file loading & caching
- selection.py  — query-driven relevance scoring
- context.py    — token-budgeted context string assembly (+ the oversized-section fix)
This file reassembles the same SystemKnowledgeEngine classmethod API as before,
so `from core.services.ai.system_knowledge_engine import SystemKnowledgeEngine`
keeps working unchanged everywhere it's already used.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from core.services.ai.system_knowledge_engine import context as _context
from core.services.ai.system_knowledge_engine import manifest as _manifest
from core.services.ai.system_knowledge_engine import selection as _selection


class SystemKnowledgeEngine:
    """Central engine for reading and dynamically serving static system knowledge from ai_knowledge/."""

    @classmethod
    def get_knowledge_dir(cls) -> Path:
        return _manifest.get_knowledge_dir()

    @classmethod
    def get_version_metadata(cls) -> Dict[str, Any]:
        return _manifest.get_version_metadata(knowledge_dir=cls.get_knowledge_dir())

    @classmethod
    def load_manifest(cls, force_refresh: bool = False) -> List[Dict[str, Any]]:
        return _manifest.load_manifest(force_refresh=force_refresh, knowledge_dir=cls.get_knowledge_dir())

    @classmethod
    def load_section_content(cls, file_name: str, force_refresh: bool = False) -> str:
        return _manifest.load_section_content(
            file_name, force_refresh=force_refresh, knowledge_dir=cls.get_knowledge_dir()
        )

    @classmethod
    def clear_cache(cls) -> None:
        _manifest.clear_cache()

    @classmethod
    def select_relevant_sections(cls, query: str = "", category: str = "") -> List[Dict[str, Any]]:
        sections = cls.load_manifest()
        return _selection.select_relevant_sections(sections, query=query, category=category)

    @classmethod
    def build_system_knowledge_context(cls, query: str = "", category: str = "", token_limit: int = 1500) -> str:
        try:
            relevant_sections = cls.select_relevant_sections(query=query, category=category)
            return _context.build_context_string(
                relevant_sections, cls.load_section_content, token_limit=token_limit
            )
        except Exception:
            import logging
            logging.getLogger(__name__).error("Failed to build system knowledge context gracefully", exc_info=True)
            return ""


__all__ = ["SystemKnowledgeEngine"]
