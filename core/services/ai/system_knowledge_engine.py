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
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List
from django.conf import settings

logger = logging.getLogger(__name__)

_KNOWLEDGE_CACHE: Dict[str, Any] = {}


class SystemKnowledgeEngine:
    """
    Central engine for reading and dynamically serving static system knowledge from ai_knowledge/.
    """

    @classmethod
    def get_knowledge_dir(cls) -> Path:
        base_dir = getattr(settings, "BASE_DIR", None)
        if base_dir:
            return Path(base_dir) / "ai_knowledge"
        return Path(__file__).resolve().parent.parent.parent.parent / "ai_knowledge"

    @classmethod
    def get_version_metadata(cls) -> Dict[str, Any]:
        """
        Exposes manifest versioning metadata for diagnostics and cache validation.
        """
        try:
            knowledge_dir = cls.get_knowledge_dir()
            manifest_path = knowledge_dir / "MANIFEST.json"
            if not manifest_path.exists():
                return {"status": "missing", "knowledge_version": "0.0.0"}

            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "status": "active",
                    "manifest_version": data.get("manifest_version", "1.0.0"),
                    "knowledge_version": data.get("knowledge_version", "1.0.0"),
                    "schema_version": data.get("schema_version", "1.0.0"),
                    "generated_at": data.get("generated_at", ""),
                    "application_version": data.get("application_version", "1.0.0"),
                }
        except Exception as exc:
            logger.warning("Failed to read knowledge version metadata: %s", exc)
            return {"status": "error", "error": str(exc), "knowledge_version": "0.0.0"}

    @classmethod
    def load_manifest(cls, force_refresh: bool = False) -> List[Dict[str, Any]]:
        try:
            if not force_refresh and "manifest" in _KNOWLEDGE_CACHE:
                return _KNOWLEDGE_CACHE["manifest"]

            knowledge_dir = cls.get_knowledge_dir()
            manifest_path = knowledge_dir / "MANIFEST.json"

            if not manifest_path.exists():
                logger.warning("ai_knowledge/MANIFEST.json not found at %s", manifest_path)
                return []

            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                sections = data.get("sections", [])
                if isinstance(sections, list):
                    _KNOWLEDGE_CACHE["manifest"] = sections
                    return sections
                return []
        except Exception as exc:
            logger.error("Failed to load ai_knowledge/MANIFEST.json gracefully: %s", exc)
            return []

    @classmethod
    def load_section_content(cls, file_name: str, force_refresh: bool = False) -> str:
        try:
            if not file_name:
                return ""

            cache_key = f"content:{file_name}"
            if not force_refresh and cache_key in _KNOWLEDGE_CACHE:
                return _KNOWLEDGE_CACHE[cache_key]

            knowledge_dir = cls.get_knowledge_dir()
            file_path = knowledge_dir / file_name

            if not file_path.exists():
                logger.warning("Knowledge file %s not found at %s", file_name, file_path)
                return ""

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                _KNOWLEDGE_CACHE[cache_key] = content
                return content
        except Exception as exc:
            logger.error("Failed to read knowledge file %s gracefully: %s", file_name, exc)
            return ""

    @classmethod
    def clear_cache(cls) -> None:
        _KNOWLEDGE_CACHE.clear()

    @classmethod
    def select_relevant_sections(
        cls, query: str = "", category: str = ""
    ) -> List[Dict[str, Any]]:
        try:
            sections = cls.load_manifest()
            if not sections:
                return []

            q = (query or "").strip().lower()
            if not q and not category:
                # Default fallback: return high-priority foundational sections
                default_ids = {"ai_operating_manual", "business_rules", "financial_rules", "response_guidelines"}
                return [s for s in sections if s.get("id") in default_ids]

            scored_sections = []
            for sec in sections:
                score = 0
                sec_category = str(sec.get("category", "")).lower()
                if category and sec_category == category.lower():
                    score += 10

                keywords = [str(kw).lower() for kw in sec.get("keywords", []) if isinstance(kw, str)]
                title = str(sec.get("title", "")).lower()
                desc = str(sec.get("description", "")).lower()

                for kw in keywords:
                    if kw in q:
                        score += 3

                # Check individual query tokens against keywords/title/desc
                tokens = [t for t in q.split() if len(t) > 2]
                for token in tokens:
                    if token in title or token in desc or any(token in kw for kw in keywords):
                        score += 1

                # Always give operating manual and response guidelines baseline relevance
                if sec.get("id") in {"ai_operating_manual", "response_guidelines"}:
                    score += 2

                if score > 0:
                    scored_sections.append((score, sec))

            scored_sections.sort(key=lambda x: x[0], reverse=True)
            return [sec for _, sec in scored_sections]
        except Exception as exc:
            logger.error("Failed section selection gracefully: %s", exc)
            return []

    @classmethod
    def build_system_knowledge_context(
        cls, query: str = "", category: str = "", token_limit: int = 1500
    ) -> str:
        """
        Formats dynamically selected system knowledge sections into a concise context string.
        Enforces token limit (estimated as 1 token ~= 4 chars).
        Fail-graceful: Returns empty string on any IO/parsing error without failing callers.
        """
        try:
            relevant_sections = cls.select_relevant_sections(query=query, category=category)
            if not relevant_sections:
                return ""

            context_blocks = []
            current_chars = 0
            max_chars = token_limit * 4

            header = "\n\n=== SYSTEM KNOWLEDGE & DOMAIN MANIFEST ==="
            current_chars += len(header)

            for sec in relevant_sections:
                content = cls.load_section_content(sec.get("file", ""))
                if not content:
                    continue

                block = f"\n\n--- [{sec.get('title', '').upper()}] ---\n{content}"
                if current_chars + len(block) > max_chars and context_blocks:
                    # Stop adding sections when token budget is reached
                    break

                context_blocks.append(block)
                current_chars += len(block)

            if not context_blocks:
                return ""

            return header + "".join(context_blocks)
        except Exception as exc:
            logger.error("Failed to build system knowledge context gracefully: %s", exc)
            return ""
