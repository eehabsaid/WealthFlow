"""App-knowledge retrieval for how / where / should questions (Zip 2).

retrieve_knowledge(query)   -> ranked, selected chunks from real sources (data-flows file generated from code,
                               doc_engine page descriptions, module/class docstrings)
find_examples(user, query)  -> thumbs-up answers the same user approved for similar questions
build_messages(...)         -> the small prompt for the reasoning path
"""

from __future__ import annotations

from typing import Any

from ai.services.app_knowledge.chunks import get_chunks
from ai.services.app_knowledge.examples import find_examples
from ai.services.app_knowledge.feedback import SOURCE_MARK, ratings_for, record_feedback
from ai.services.app_knowledge.prompt import build_messages, fallback_text, select_chunks
from ai.services.app_knowledge.question_kind import is_workflow_question
from ai.services.app_knowledge.scoring import rank

__all__ = ["SOURCE_MARK", "build_data_slice", "build_messages", "fallback_text", "find_examples", "is_workflow_question",
           "ratings_for", "record_feedback", "retrieve_knowledge"]


def build_data_slice(user, *args, **kwargs):
    """Live-data lines for workflow answers; supplied by the host pack (none without one)."""
    from ai.packs import ext
    hook = ext("data_slice")
    return hook(user, *args, **kwargs) if hook else ""


def retrieve_knowledge(query: str, max_chunks: int = 4, max_chars: int = 2400) -> list[tuple[float, dict[str, Any]]]:
    """[(score, chunk)] best first, already cut to the prompt budget."""
    return select_chunks(rank(query, get_chunks()), max_chunks, max_chars)
