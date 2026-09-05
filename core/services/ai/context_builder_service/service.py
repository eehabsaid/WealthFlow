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

from core.services.ai.context_builder_service.business_data import fetch_grounding_business_data
from core.services.ai.context_builder_service.constants import DEFAULT_CORE_SERVICES, TOPIC_KEYWORD_MAP
from core.services.ai.context_builder_service.formatting import split_payload_blocks, summarize_payload
from core.services.ai.context_builder_service.prompt import build_system_prompt

logger = logging.getLogger(__name__)


class ContextBuilderService:
    """
    Assembles structured financial context for AI reasoning and formats model messages.
    Enforces priority-based context assembly to prevent JSON truncation syntax corruption.
    """

    def get_token_budget(self) -> int:
        budget_str = AppSettings.get("ai_context_token_budget", "2048")
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
        q = (query or "").lower().strip()
        selected = list(DEFAULT_CORE_SERVICES)

        from core.services.financial_advisor.registry import get_available_advisor_services
        available_services = get_available_advisor_services()

        for service_key in available_services:
            clean_key = service_key.replace("_", " ").lower()
            if any(term in q for term in clean_key.split()):
                if service_key not in selected:
                    selected.append(service_key)

        for service_key, keywords in TOPIC_KEYWORD_MAP.items():
            if any(kw in q for kw in keywords):
                if service_key not in selected:
                    selected.append(service_key)

        return selected

    def build_system_prompt(self, user: Any = None, query: str = "") -> str:
        return build_system_prompt(user=user, query=query)

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
        token_budget = self.get_token_budget()
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

        # 2a. Deterministic business-data grounding FIRST (balance, certificates,
        # expenses, salary, fixed assets/gold, market data) — only for topically-matched
        # providers, so this never fires for unrelated small talk. See business_data.py
        # docstring. Prioritized ahead of the generic advisor blocks below because this
        # is the literal, real answer to what the user actually asked about.
        biz_sources, biz_high, biz_low = fetch_grounding_business_data(user, user_query)
        sources.extend(biz_sources)
        high_priority_blocks.extend(biz_high)
        low_priority_blocks.extend(biz_low)

        for key in service_keys:
            payload = get_financial_advisor_payload(key)
            if not payload:
                continue
            sources.append(key)
            high, low = split_payload_blocks(key, payload)
            high_priority_blocks.extend(high)
            low_priority_blocks.extend(low)

        # 3. Assemble System Context String safely within its reserved data budget
        # (independent of system_instruction size — see MIN_DATA_CHARS above).
        context_parts = []
        data_chars_used = 0
        for block in high_priority_blocks:
            if data_chars_used + len(block) <= data_chars_budget:
                context_parts.append(block)
                data_chars_used += len(block)

        # Append degradable low priority blocks section-by-section cleanly
        for block in low_priority_blocks:
            if data_chars_used + len(block) <= data_chars_budget:
                context_parts.append(block)
                data_chars_used += len(block)
            else:
                # Omit low-priority detail block cleanly without breaking JSON syntax
                logger.info("Token budget reached: Omitted detailed timeline block cleanly.")
                break

        full_context_str = "\n".join(context_parts)
        system_content = f"{system_instruction}\n\n=== FINANCIAL CONTEXT DATA ===\n{full_context_str}"

        messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]

        # 4. Append Historical Messages if budget permits
        current_tokens = self.estimate_tokens(system_content)
        user_q_tokens = self.estimate_tokens(user_query)
        available_history_budget = token_budget - current_tokens - user_q_tokens

        formatted_history: list[dict[str, str]] = []
        if history_messages and available_history_budget > 100:
            history_list = list(history_messages)
            accumulated_tokens = 0
            for msg in reversed(history_list):
                msg_str = f"{msg.role}: {msg.content}"
                msg_tokens = self.estimate_tokens(msg_str)
                if accumulated_tokens + msg_tokens > available_history_budget:
                    break
                accumulated_tokens += msg_tokens
                formatted_history.insert(0, {"role": msg.role, "content": msg.content})

        messages.extend(formatted_history)
        messages.append({"role": "user", "content": user_query})

        return messages, sources
