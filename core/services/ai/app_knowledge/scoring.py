"""Ranks chunks: lexical (IDF-weighted token overlap, same tokenizer as codebase_search) + optional
embedding bonus on the few best lexical candidates. If embeddings are unavailable it is lexical only."""

from __future__ import annotations

import math
import re
from typing import Any

from core.services.ai.app_knowledge.query_terms_fr_de import fold, foreign_terms
from core.services.ai.codebase_search import query_tokens, tokenize

# Query-side normalisation only (everyday wording -> the words the app's own text uses). Not answers.
_SYNONYMS = {
    "bought": ("purchase",), "buy": ("purchase",), "buying": ("purchase",), "purchased": ("purchase",),
    "paid": ("payment",), "pay": ("payment",), "cost": ("price",), "spent": ("expense",), "spend": ("expense",),
    "owned": ("asset",), "own": ("asset",), "sold": ("sale",), "sell": ("sale",),
}
# Arabic question words -> the English words the app's own text uses (query side only; the knowledge stays English)
_AR_TERMS = {
    "أصل": ("asset",), "اصل": ("asset",), "أصول": ("asset",), "اصول": ("asset",), "ثابتة": ("fixed", "asset"),
    "مصروف": ("expense",), "مصروفات": ("expense",), "مصاريف": ("expense",), "نفقات": ("expense",),
    "شراء": ("purchase", "price"), "اشتريت": ("purchase", "price"), "سعر": ("price",), "ثمن": ("price",), "تكلفة": ("cost", "price"),
    "لابتوب": ("asset", "other", "purchase"), "كمبيوتر": ("asset", "other", "purchase"), "هاتف": ("asset", "other", "purchase"),
    "سيارة": ("vehicle", "asset"), "عقار": ("real", "estate", "asset"), "شقة": ("real", "estate", "asset"),
    "تجديد": ("renovation",), "ترميم": ("renovation",), "أثاث": ("furniture",), "اثاث": ("furniture",),
    "بطاقة": ("card",), "ائتمان": ("credit", "card"), "ائتمانية": ("credit", "card"), "رسوم": ("fee",),
    "بنك": ("bank",), "حساب": ("bank", "account"), "رصيد": ("balance",), "نقد": ("cash",), "نقدي": ("cash",),
    "ذهب": ("gold",), "راتب": ("salary",), "شهادة": ("certificate",), "فائدة": ("interest",),
    "سجل": ("record",), "أسجل": ("record",), "اسجل": ("record",), "أضيف": ("add", "record"), "اضيف": ("add", "record"),
    "أحتسب": ("record", "count"), "احتسب": ("record", "count"), "بيع": ("sale", "sell"), "بعت": ("sale", "sell"),
    "ميزانية": ("budget",), "تحويل": ("transfer",), "صافي": ("net", "worth"),
}
_AR_WORD = re.compile(r"[\u0600-\u06FF]+")
_AR_PREFIXES = ("وال", "بال", "لل", "ال", "و", "ب", "ل")
SEMANTIC_CANDIDATES = 8
SEMANTIC_WEIGHT = 1.0
# generated data-flow facts and page descriptions describe what the app does for the user; docstrings explain internals
SOURCE_BOOST = {"flow": 1.3, "page": 1.1, "code": 1.0}


def semantic_enabled() -> bool:
    """Off by default: the embedding call can stall for seconds and loads a second model next to the chat model,
    which hurts on small machines. Lexical ranking already finds the right chunks. AppSettings ai_knowledge_semantic."""
    from core.models import AppSettings

    return str(AppSettings.get("ai_knowledge_semantic", "false")).strip().lower() in ("true", "1", "yes", "on")


def expand_query(query: str) -> set[str]:
    tokens = set(query_tokens(fold(query)))  # fold: accents/umlauts no longer split FR/DE words into fragments
    tokens.update(foreign_terms(query))
    for word in _AR_WORD.findall(query or ""):
        for cand in (word, *(word[len(p):] for p in _AR_PREFIXES if word.startswith(p) and len(word) - len(p) >= 2)):
            tokens.update(_AR_TERMS.get(cand, ()))
    for t in list(tokens):
        tokens.update(_SYNONYMS.get(t, ()))
    return tokens


def _chunk_tokens(chunk: dict[str, Any]) -> tuple[set[str], set[str]]:
    if "_tok" not in chunk:
        chunk["_tok"] = (tokenize(chunk["text"]), tokenize(chunk["title"] + " " + chunk["location"]))
    return chunk["_tok"]


def lexical_rank(query: str, chunks: list[dict[str, Any]]) -> list[tuple[float, dict[str, Any]]]:
    q = expand_query(query)
    if not q:
        return []
    df: dict[str, int] = {}
    for c in chunks:
        body, head = _chunk_tokens(c)
        for t in q & (body | head):
            df[t] = df.get(t, 0) + 1
    n = max(len(chunks), 1)
    scored = []
    for c in chunks:
        body, head = _chunk_tokens(c)
        s = sum(math.log(1 + n / df[t]) * (1.0 + (0.6 if t in head else 0.0)) for t in q & (body | head))
        if s > 0:
            scored.append((s * SOURCE_BOOST.get(c["source"], 1.0), c))
    scored.sort(key=lambda sc: (-sc[0], len(sc[1]["text"])))
    return scored


def rank(query: str, chunks: list[dict[str, Any]], limit: int = 12) -> list[tuple[float, dict[str, Any]]]:
    lex = lexical_rank(query, chunks)[:limit]
    if len(lex) < 2:
        return lex
    if not semantic_enabled():
        return lex
    try:
        from core.services.ai.retrieval import embeddings

        head = lex[:SEMANTIC_CANDIDATES]
        sem = embeddings.semantic_scores(query, {c["id"]: f"{c['title']}. {c['text']}" for _, c in head})
    except Exception:  # retrieval must never break chat
        sem = None
    if not sem:
        return lex
    top = max(s for _, s in lex) or 1.0
    rescored = [(s / top + SEMANTIC_WEIGHT * sem.get(c["id"], 0.0), c) for s, c in head] + [(s / top, c) for s, c in lex[SEMANTIC_CANDIDATES:]]
    rescored.sort(key=lambda sc: -sc[0])
    return rescored
