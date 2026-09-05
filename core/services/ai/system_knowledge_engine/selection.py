"""
Query-driven relevance scoring for system knowledge sections.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Always-included foundational sections when there's no query/category to score against.
DEFAULT_SECTION_IDS = {"ai_operating_manual", "business_rules", "financial_rules", "response_guidelines"}

# Sections given a small baseline relevance boost regardless of query match.
BASELINE_BOOST_IDS = {"ai_operating_manual", "response_guidelines"}


def select_relevant_sections(
    sections: List[Dict[str, Any]], query: str = "", category: str = ""
) -> List[Dict[str, Any]]:
    try:
        if not sections:
            return []

        q = (query or "").strip().lower()
        if not q and not category:
            return [s for s in sections if s.get("id") in DEFAULT_SECTION_IDS]

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

            if sec.get("id") in BASELINE_BOOST_IDS:
                score += 2

            if score > 0:
                scored_sections.append((score, sec))

        scored_sections.sort(key=lambda x: x[0], reverse=True)
        return [sec for _, sec in scored_sections]
    except Exception as exc:
        logger.error("Failed section selection gracefully: %s", exc)
        return []
