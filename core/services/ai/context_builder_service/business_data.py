"""
Deterministic business-data grounding for the AI chat system context.

Financial Advisor services (overview, cash_flow, wealth_growth, etc.) are
NOT the only real data users ask about — balances, bank certificates,
expenses, salary, fixed assets, and live gold/exchange rates all live in
the separate Data Provider Registry (core/services/ai/providers/registry.py)
and are otherwise only reachable if the model itself decides to call the
query_application_data tool.

Smaller/local models don't always make that call reliably (see: a user
asking "how much gold do I own" getting a guessed answer instead of a real
one). To make grounding deterministic instead of a coin flip, this module
mirrors the DEFAULT_CORE_SERVICES pattern already used for advisor
services: whenever the user's query has a clear topical match against a
registered data provider (via the existing relevance-scoring logic),
that provider's real data is fetched and injected into the system context
up front — the model never has to "decide" to look it up.

require_signal=True is used here (as opposed to the query_application_data
tool's own default) so an unrelated/generic message does NOT trigger a
full dump of every business data provider — only real topical matches do.
"""

from __future__ import annotations

from typing import Any

from core.services.ai.context_builder import AIContextBuilder
from core.services.ai.context_builder_service.formatting import split_payload_blocks


def fetch_grounding_business_data(user: Any, user_query: str) -> tuple[list[str], list[str], list[str]]:
    """
    Returns (sources, high_priority_blocks, low_priority_blocks) for any data
    provider whose capabilities topically match user_query. Empty query matches
    yield empty results (no forced full-registry dump) — see require_signal above.
    """
    sources: list[str] = []
    high_priority_blocks: list[str] = []
    low_priority_blocks: list[str] = []

    business_data = AIContextBuilder.build_business_context(
        user=user, search_query=user_query, require_signal=True
    )

    for key, payload in business_data.items():
        if key.startswith("_") or key.endswith("_error"):
            continue
        if not payload:
            continue

        sources.append(key)
        high, low = split_payload_blocks(key, payload)
        high_priority_blocks.extend(high)
        low_priority_blocks.extend(low)

    return sources, high_priority_blocks, low_priority_blocks
