"""
AI Knowledge Engine.

Manages distilled long-term domain knowledge entries (business rules, codebase architecture,
user preferences, app evolution facts) for AI system prompt context injection.
"""

from __future__ import annotations

import logging
from typing import Any
from core.models import AIKnowledgeEntry

logger = logging.getLogger(__name__)


class AIKnowledgeEngine:
    """
    Central engine for reading, storing, and summarizing distilled long-term knowledge entries.
    """

    @classmethod
    def get_active_knowledge_entries(cls, category: str | None = None) -> list[AIKnowledgeEntry]:
        qs = AIKnowledgeEntry.objects.filter(is_active=True)
        if category:
            qs = qs.filter(category=category)
        return list(qs.order_by("-updated_at"))

    @classmethod
    def record_knowledge_entry(
        cls,
        key: str,
        title: str,
        content: str,
        category: str = "business_rule",
        confidence: float = 1.0,
        source: str = "autonomous_learning",
    ) -> AIKnowledgeEntry:
        clean_key = str(key or "").strip().lower()
        entry, _created = AIKnowledgeEntry.objects.update_or_create(
            key=clean_key,
            defaults={
                "title": str(title or "").strip(),
                "content": str(content or "").strip(),
                "category": category,
                "confidence": confidence,
                "source": source,
                "is_active": True,
            },
        )
        return entry

    @classmethod
    def extract_knowledge_from_conversation(
        cls, user: Any, user_query: str, ai_response: str
    ) -> list[AIKnowledgeEntry]:
        """
        Synthesizes conversation interactions to extract long-term user preferences or directives.
        """
        extracted = []
        q_lower = (user_query or "").lower()

        # Directives on asset preference
        if "gold" in q_lower or "certificates" in q_lower or "cash" in q_lower:
            entry = cls.record_knowledge_entry(
                key="pref_asset_allocation_focus",
                title="User Focus Asset Classes",
                content="User actively prioritizes liquid holdings in Gold, Bank Certificates, and EGP Cash.",
                category="user_preference",
                confidence=0.95,
                source="user_conversation",
            )
            extracted.append(entry)

        return extracted

    @classmethod
    def build_knowledge_context(cls, user: Any = None, query: str = "") -> str:
        """
        Formats system knowledge manifest and active database knowledge entries into concise system directives.
        """
        from core.services.ai.system_knowledge_engine import SystemKnowledgeEngine

        parts = []
        system_knowledge = SystemKnowledgeEngine.build_system_knowledge_context(query=query)
        if system_knowledge:
            parts.append(system_knowledge)

        entries = cls.get_active_knowledge_entries()
        if entries:
            lines = ["\n\nDYNAMIC USER & APPLICATION PREFERENCES:"]
            for entry in entries[:15]:  # Top 15 knowledge entries
                lines.append(f"- [{entry.category.upper()}] {entry.title}: {entry.content}")
            parts.append("\n".join(lines))

        return "".join(parts)

