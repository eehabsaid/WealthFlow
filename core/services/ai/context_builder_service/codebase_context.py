"""Codebase retrieval for the default chat path (backlog item 2).

Only fires for questions that are clearly about the code (is_codebase_question). Adds one
compact, high-priority block of the top ranked classes. Cost is prompt tokens only:
CODEBASE_BLOCK_MAX_CHARS/4 = 300 tokens at ~45 tok/s prefill = ~6.7 s worst case; no extra LLM
or embedding call."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from core.services.ai.codebase_indexer import CodebaseIndexer
from core.services.ai.codebase_search import query_tokens

logger = logging.getLogger(__name__)

CODEBASE_TOP_N = 5
CODEBASE_BLOCK_MAX_CHARS = 1200
_CODE_Q = re.compile(
    r"\b(codebase|source code|architecture|implemented|endpoints?|which (class|file|module)|"
    r"where (is|are|do we|does)\b.{0,50}\b(defined|implemented|handled|handle|live|lives)|"
    r"what (class|file|module)|reuse)\b", re.I)


def is_codebase_question(query: str) -> bool:
    return bool(_CODE_Q.search(query or "")) and bool(query_tokens(query))


def build_codebase_block(query: str) -> str | None:
    try:
        res: dict[str, Any] = CodebaseIndexer.get_index(search_term=query)
    except Exception as exc:
        logger.info("Codebase retrieval skipped: %s", exc)
        return None
    hits = (res.get("architecture_index") or [])[:CODEBASE_TOP_N]
    if not hits:
        return None
    rows = [{"class": h["class_name"], "file": h["location"], "type": h["module_type"],
             "does": h.get("docstring", "")[:100], "methods": h.get("methods", [])[:6]} for h in hits]
    block = "codebase_matches: " + json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    while len(block) > CODEBASE_BLOCK_MAX_CHARS and rows:
        rows.pop()
        block = "codebase_matches: " + json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    return block if rows else None
