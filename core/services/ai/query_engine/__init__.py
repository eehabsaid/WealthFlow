"""General query engine for the AI chat: declared capabilities + typed owner-scoped read-only requests
+ deterministic slot filling + code-generated answers. See engine.answer()."""

from .engine import answer, is_enabled
from .facts import build_facts
from .registry import get_capabilities, get_capability
from .slots import Routing, route
from .spec import Capability, QueryRequest, QueryResult

__all__ = ["Capability", "QueryRequest", "QueryResult", "Routing", "answer", "build_facts",
           "get_capabilities", "get_capability", "is_enabled", "route"]
