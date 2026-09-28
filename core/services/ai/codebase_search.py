"""Ranked, token-based search over the CodebaseIndexer entries (backlog item 2).

The old filter was `whole_query in text`, which can never match a natural-language
question ("where do we handle bank card renewal fees?"). This tokenises the query and
each entry (splitting CamelCase / snake_case / paths), weights hits by field, and keeps
a big bonus for the legacy exact-substring case so tool calls like 'ExpenseService'
still rank that class first. Pure Python, no LLM, no embeddings (embedding hundreds of
classes per query would cost far more than it saves at this hardware's speed)."""

from __future__ import annotations

import re
from typing import Any

_WORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
# Words that say "this is a code question" or appear in nearly every path/entry.
GENERIC = frozenset({
    "core", "service", "services", "view", "views", "model", "models", "class", "classes",
    "file", "files", "code", "codebase", "app", "application", "function", "functions",
    "handle", "handles", "handled", "does", "where", "which", "what", "how", "the", "and",
    "for", "our", "with", "implemented", "implement", "logic", "module", "modules",
    "where's", "are", "this", "that", "from", "have", "has", "can", "you", "use", "used",
})
W_NAME, W_PATH, W_DOC, W_METHOD, W_EXACT = 3.0, 2.0, 1.0, 1.0, 5.0


def tokenize(text: str) -> set[str]:
    out: set[str] = set()
    for chunk in re.split(r"[^A-Za-z0-9]+", text or ""):
        for w in _WORD.findall(chunk):
            w = w.lower()
            if len(w) < 3:
                continue
            out.add(w)
            if len(w) > 4 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
                out.add(w[:-1])
            if len(w) > 5 and w.endswith("ing"):
                out.add(w[:-3])  # mirroring -> mirror
    return out


def query_tokens(query: str) -> set[str]:
    return {t for t in tokenize(query) if t not in GENERIC}


def _score(entry: dict[str, Any], q: set[str], raw: str) -> float:
    name = tokenize(entry.get("class_name", ""))
    path = tokenize(entry.get("location", ""))
    doc = tokenize(entry.get("docstring", ""))
    meth = tokenize(" ".join(entry.get("methods", [])))
    score = (W_NAME * len(q & name) + W_PATH * len(q & path)
             + W_DOC * len(q & doc) + W_METHOD * min(len(q & meth), 3))
    if raw and raw in (f"{entry.get('class_name', '')} {entry.get('location', '')} "
                       f"{entry.get('docstring', '')} {' '.join(entry.get('methods', []))}").lower():
        score += W_EXACT
    return score


def rank_entries(entries: list[dict[str, Any]], query: str, limit: int = 50) -> list[dict[str, Any]]:
    """Entries with score > 0, best first (ties: shorter path = more central)."""
    raw = (query or "").strip().lower()
    q = query_tokens(query)
    if not q and not raw:
        return entries[:limit]
    scored = [(s, e) for e in entries if (s := _score(e, q, raw)) > 0]
    scored.sort(key=lambda se: (-se[0], len(se[1].get("location", ""))))
    return [e for _, e in scored[:limit]]
