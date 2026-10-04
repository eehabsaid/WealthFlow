"""App-knowledge retrieval for how / where / should questions (Zip 2).

retrieve_knowledge(query)   -> ranked, selected chunks from real sources (data-flows file generated from code,
                               doc_engine page descriptions, module/class docstrings)
find_examples(user, query)  -> thumbs-up answers the same user approved for similar questions
build_messages(...)         -> the small prompt for the reasoning path
"""

from __future__ import annotations

from typing import Any

from .chunks import get_chunks
from .data_slice import build_data_slice
from .examples import find_examples
from .feedback import SOURCE_MARK, ratings_for, record_feedback
from .prompt import build_messages, select_chunks
from .question_kind import is_workflow_question
from .scoring import rank

__all__ = ["SOURCE_MARK", "build_data_slice", "build_messages", "find_examples", "is_workflow_question",
           "ratings_for", "record_feedback", "retrieve_knowledge"]


def retrieve_knowledge(query: str) -> list[tuple[float, dict[str, Any]]]:
    """[(score, chunk)] best first, already cut to the prompt budget."""
    return select_chunks(rank(query, get_chunks()))
