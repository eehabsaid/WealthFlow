"""General query engine for the AI chat: declared capabilities + typed owner-scoped read-only requests
+ deterministic slot filling + code-generated answers. See engine.answer()."""

from ai.services.query_engine.engine import answer, is_enabled
from ai.services.query_engine.facts import build_facts
from ai.services.query_engine.registry import get_capabilities, get_capability
from ai.services.query_engine.slots import Routing, route
from ai.services.query_engine.verified import verified_for_model
from ai.services.query_engine.spec import Capability, QueryRequest, QueryResult

__all__ = ["Capability", "QueryRequest", "QueryResult", "Routing", "answer", "build_facts",
           "get_capabilities", "get_capability", "is_enabled", "route", "verified_for_model"]
