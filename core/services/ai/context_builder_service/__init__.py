"""
AI Context Builder Service package.

Split from a single context_builder_service.py (>200 lines) into:
- constants.py     — DEFAULT_CORE_SERVICES, TOPIC_KEYWORD_MAP
- formatting.py     — payload -> Markdown block helpers (shared)
- prompt.py         — system prompt & guardrails builder
- business_data.py  — deterministic business-data provider grounding
- service.py        — the ContextBuilderService class itself

Re-exports ContextBuilderService (and the constants, for any external
code/tests importing them from the old flat module path) so existing
`from core.services.ai.context_builder_service import ContextBuilderService`
imports keep working unchanged.
"""

from core.services.ai.context_builder_service.constants import (
    DEFAULT_CORE_SERVICES,
    TOPIC_KEYWORD_MAP,
)
from core.services.ai.context_builder_service.service import ContextBuilderService

__all__ = ["ContextBuilderService", "DEFAULT_CORE_SERVICES", "TOPIC_KEYWORD_MAP"]
