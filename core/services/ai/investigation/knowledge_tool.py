"""app_knowledge_search: the app's own documentation (page descriptions, data-flow notes, docstrings, approved answers)."""

from __future__ import annotations


def knowledge_search(user, params):
    from core.services.ai import app_knowledge as ak

    query = str(params.get("query") or "").strip()
    if not query:
        return {"error": "query is required, e.g. 'where do I record a laptop purchase'"}
    ranked = ak.retrieve_knowledge(query, 5, 3600)
    if not ranked:
        return {"query": query, "chunks": [], "note": "no documentation matched; investigate with data or code tools instead"}
    return {"query": query, "chunks": [{"id": c.get("id"), "text": str(c.get("text") or "")[:1100]} for _, c in ranked]}
