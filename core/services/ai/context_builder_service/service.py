"""
AI Context Builder Service.

Assembles relevant financial data context from existing financial_advisor services
via the centralized registry layer (zero duplicated math, zero direct concrete class coupling).
Formats data, enforces system prompt guardrails, and applies priority-based context token budgeting.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

from core.models import AppSettings, AIMessage
from core.services.financial_advisor.registry import get_financial_advisor_payload

from core.services.ai.context_builder_service.advisor_semantic import semantic_advisor_matches
from core.services.ai.context_builder_service.business_data import fetch_grounding_business_data
from core.services.ai.context_builder_service.codebase_context import build_codebase_block, is_codebase_question
from core.services.ai.context_builder_service.constants import (
    DEFAULT_CORE_SERVICES,
    TOPIC_KEYWORD_MAP,
    match_advisor_services_by_name,
)
from core.services.ai.context_builder_service.formatting import split_payload_blocks, summarize_payload
from core.services.ai.context_builder_service.history import select_history
from core.services.ai.context_builder_service.prompt import build_system_prompt

logger = logging.getLogger(__name__)


def _owner_of(block: str, sources: list[str]) -> str:
    """Source of a business-data block: its header is '### <Provider>_<part> Payload Data:' (see summarize_payload)."""
    head = block.split("\n", 1)[0].lower().replace(" ", "_")
    return next((s for s in sorted(sources, key=len, reverse=True) if s.lower() in head), "")


def _fit_blocks(high: list[str], low: list[str], budget: int, owner: dict[int, str]) -> tuple[list[str], set[str]]:
    """Choose the blocks that fit `budget`. Every source gets its most important block considered before any source gets a
    second one (round robin), so one data-heavy topic (e.g. expenses) can no longer starve another matched source
    (e.g. the wealth forecast). A block that does not fit is skipped, not a reason to stop. Order of the chosen blocks is
    kept as assembled (priority order). Returns (blocks, sources that made it in)."""
    chosen: set[int] = set()
    used = 0

    def take(pool: list[str]) -> None:
        nonlocal used
        queues: dict[str, list[str]] = {}
        for blk in pool:
            queues.setdefault(owner.get(id(blk), ""), []).append(blk)
        while any(queues.values()):
            for key in list(queues):
                while queues[key]:
                    blk = queues[key].pop(0)
                    if used + len(blk) <= budget:
                        chosen.add(id(blk))
                        used += len(blk)
                        break          # one block per source per round
    take(high)
    take(low)
    ordered = [b for b in (*high, *low) if id(b) in chosen]
    return ordered, {owner.get(id(b), "") for b in ordered}


class ContextBuilderService:
    """
    Assembles structured financial context for AI reasoning and formats model messages.
    Enforces priority-based context assembly to prevent JSON truncation syntax corruption.
    """

    def get_token_budget(self, user: Any = None) -> int:
        budget_str = AppSettings.get("ai_context_token_budget", "2048", user=user)
        try:
            val = int(budget_str)
            return max(1000, val)
        except (ValueError, TypeError):
            return 2048

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    def determine_relevant_services(self, query: str) -> list[str]:
        """Returns ONLY the advisor services whose name or topic keywords actually
        match the query. DEFAULT_CORE_SERVICES is no longer unconditionally
        prepended here — see assemble_messages, which falls back to it only when
        nothing (neither this nor business-data grounding) matched at all. An
        unconditional default here previously meant 4-5 unrelated advisor
        payloads (overview/cash_flow/goal_planning/risk_analysis/...) got
        dumped into every single query, crowding out the real, topically-matched
        answer under the token budget (confirmed via core_aimessage.sources on
        a real "list daily expenses" query pulling in 5 unrelated sources)."""
        q = (query or "").lower().strip()
        selected: list[str] = []

        from core.services.financial_advisor.registry import get_available_advisor_services
        available_services = get_available_advisor_services()

        for service_key in match_advisor_services_by_name(q, available_services):
            if service_key not in selected:
                selected.append(service_key)

        for service_key, keywords in TOPIC_KEYWORD_MAP.items():
            if any(kw in q for kw in keywords):
                if service_key not in selected:
                    selected.append(service_key)

        return selected

    def build_system_prompt(self, user: Any = None, query: str = "") -> str:
        # Cap the system-knowledge-manifest section as a fraction of the real
        # configured budget instead of a hardcoded 1500-token limit that
        # ignored ai_context_token_budget entirely.
        knowledge_token_limit = min(1500, max(300, self.get_token_budget(user) // 4))
        memory_token_limit = max(150, self.get_token_budget(user) // 5)   # the memory index takes at most a fifth of the UI-set budget
        return build_system_prompt(user=user, query=query, knowledge_token_limit=knowledge_token_limit, memory_token_limit=memory_token_limit)

    def summarize_payload(self, service_key: str, payload: dict[str, Any]) -> str:
        return summarize_payload(service_key, payload)

    def assemble_messages(
        self,
        user_query: str,
        history_messages: Sequence[AIMessage] | None = None,
        user: Any = None,
    ) -> tuple[list[dict[str, str]], list[str]]:
        """
        Assembles message list for the AI provider along with source service/provider names.
        Enforces PRIORITY-BASED SECTION-AWARE CONTEXT ASSEMBLY:
        1. System Directives & Guardrails (Preserved 100%)
        2. Intent-Matched System Knowledge Manifest (Preserved 100%)
        3. Deterministic Financial Summaries & Pre-Computed Metrics (Preserved First)
        4. Category & Yearly Summary Breakdowns (Preserved Second)
        5. Historical Monthly Timeline Entries & Raw Items (Degraded Cleanly Section-by-Section if Budget Limit Reached)
        Guarantees 0% broken JSON syntax.
        """
        token_budget = self.get_token_budget(user)
        max_chars = token_budget * 4

        # Guaranteed minimum room for actual financial/business data, independent
        # of how large the system prompt + knowledge manifest turned out to be.
        # Without this floor, an oversized system_instruction (guardrails + system
        # knowledge context) can consume the entire budget on its own, silently
        # leaving the "=== FINANCIAL CONTEXT DATA ===" section empty on every
        # single chat turn — which is exactly what was happening before this fix.
        MIN_DATA_CHARS = 8000

        service_keys = self.determine_relevant_services(user_query)

        # 1. Gather System Instruction (Priority 1 & 2)
        system_instruction = self.build_system_prompt(user=user, query=user_query)
        data_chars_budget = max(max_chars - len(system_instruction) - 50, MIN_DATA_CHARS)

        # 2. Separate Payload Data into High-Priority Summaries vs Low-Priority Timelines
        high_priority_blocks = []
        low_priority_blocks = []
        sources = []
        block_owner: dict[int, str] = {}   # id(block) -> the source it came from (fair budget sharing)

        # 2a. Deterministic business-data grounding FIRST (balance, certificates,
        # expenses, salary, fixed assets/gold, market data) — only for topically-matched
        # providers, so this never fires for unrelated small talk. See business_data.py
        # docstring. Prioritized ahead of the generic advisor blocks below because this
        # is the literal, real answer to what the user actually asked about.
        biz_sources, biz_high, biz_low = fetch_grounding_business_data(user, user_query)
        sources.extend(biz_sources)
        high_priority_blocks.extend(biz_high)
        low_priority_blocks.extend(biz_low)
        for blk in (*biz_high, *biz_low):
            block_owner[id(blk)] = _owner_of(blk, biz_sources)

        # 2b. Codebase retrieval, only for clearly code/architecture questions.
        if is_codebase_question(user_query):
            code_block = build_codebase_block(user_query)
            if code_block:
                sources.append("codebase_index")
                high_priority_blocks.append(code_block)

        # Nothing matched lexically or via business data: try semantic advisor matching
        # (one cached query embedding; [] on any failure) before the broad default set.
        if not service_keys and not sources:
            from core.services.financial_advisor.registry import get_available_advisor_services
            service_keys = semantic_advisor_matches(user_query, get_available_advisor_services())
            if not service_keys:
                service_keys = list(DEFAULT_CORE_SERVICES)

        for key in service_keys:
            payload = get_financial_advisor_payload(key, user)
            if not payload:
                continue
            sources.append(key)
            high, low = split_payload_blocks(key, payload)
            high_priority_blocks.extend(high)
            low_priority_blocks.extend(low)
            for blk in (*high, *low):
                block_owner[id(blk)] = key

        # 3. Assemble System Context String safely within its reserved data budget
        # (independent of system_instruction size — see MIN_DATA_CHARS above).
        context_parts, _included = _fit_blocks(high_priority_blocks, low_priority_blocks, data_chars_budget, block_owner)

        full_context_str = "\n".join(context_parts)
        system_content = f"{system_instruction}\n\n=== FINANCIAL CONTEXT DATA ===\n{full_context_str}"

        messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]

        # 4. Append Historical Messages if budget permits
        current_tokens = self.estimate_tokens(system_content)
        user_q_tokens = self.estimate_tokens(user_query)
        available_history_budget = token_budget - current_tokens - user_q_tokens

        formatted_history = select_history(history_messages, available_history_budget, self.estimate_tokens)

        messages.extend(formatted_history)
        messages.append({"role": "user", "content": user_query})

        return messages, sources
