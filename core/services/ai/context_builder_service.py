"""
AI Context Builder Service.

Assembles relevant financial data context from existing financial_advisor services
via the centralized registry layer (zero duplicated math, zero direct concrete class coupling).
Formats data, enforces system prompt guardrails, and applies priority-based context token budgeting.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Sequence

from core.models import AppSettings, AIMessage
from core.services.financial_advisor.registry import get_financial_advisor_payload

logger = logging.getLogger(__name__)

DEFAULT_CORE_SERVICES = ["overview", "cash_flow", "goal_planning", "risk_analysis"]

TOPIC_KEYWORD_MAP: dict[str, list[str]] = {
    "portfolio_optimizer": ["portfolio", "allocation", "rebalance", "diversification", "asset class"],
    "wealth_growth": ["growth", "future wealth", "long term", "projection", "forecast", "compounding"],
    "spending_intelligence": ["spending", "expense", "category", "budget", "trend", "cost", "discretionary"],
    "opportunity_detection": ["opportunity", "idle cash", "yield", "optimize", "savings", "return"],
    "performance": ["performance", "return", "historical", "gain", "loss", "metric"],
    "what_if_simulator": ["what if", "simulate", "simulation", "salary increase", "windfall"],
    "scenario_planner": ["scenario", "recession", "stress test", "crisis", "inflation"],
}


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
        base_prompt = AppSettings.get(
            "ai_system_prompt",
            "You are the WealthFlow AI Financial Advisor. Answer financial questions strictly using provided data.",
        ).strip()

        home_currency = AppSettings.get("home_currency", "EGP")
        if user and hasattr(user, "profile") and getattr(user.profile, "preferred_currency", None):
            pref_curr = getattr(user.profile, "preferred_currency")
            if hasattr(pref_curr, "code"):
                home_currency = str(pref_curr.code).strip()
            elif pref_curr:
                home_currency = str(pref_curr).strip()

        guardrails = (
            "\n\nCRITICAL DIRECTIVES:\n"
            "1. You MUST reason strictly and exclusively using the real-time financial context data provided below.\n"
            "2. Every metric, balance, forecast, and figure in your response MUST come directly from the provided financial context payload.\n"
            "3. Do NOT make up, guess, or fabricate financial figures or details that are not present in the data.\n"
            "4. If the user asks about metrics or details not present in the provided context, state clearly that the specific metric is not available in the current financial payload.\n"
            "5. CURRENCY & FORMATTING STANDARDS:\n"
            f"   - Primary Currency Context: The user's active primary currency is '{home_currency}'.\n"
            "   - Detect and use the EXACT currency code associated with each account, balance, certificate, or asset in the payload (e.g. EGP, USD, EUR, SAR).\n"
            f"   - If no currency code is explicitly specified for a monetary figure, use the user's primary currency code '{home_currency}'.\n"
            "   - NEVER default to '$' or USD for non-USD currencies! Only use '$' if the currency in the payload is explicitly USD.\n"
            f"   - Format ALL monetary amounts with thousands separators and explicit currency codes (e.g. '292,900.00 {home_currency}' or '15,000.00 SAR').\n"
            "   - NEVER output raw JSON objects, raw dictionaries, or raw internal keys (such as 'portfolio_optimizer_asset_cash').\n"
            "   - Always map internal keys to human-readable labels (e.g. 'portfolio_optimizer_asset_cash' -> 'Cash', 'portfolio_optimizer_asset_certificates' -> 'Bank Certificates', 'portfolio_optimizer_asset_gold' -> 'Gold', 'portfolio_optimizer_asset_real_estate' -> 'Real Estate', 'portfolio_optimizer_asset_vehicles' -> 'Vehicles', 'portfolio_optimizer_asset_other_assets' -> 'Other Assets').\n"
            "   - Present financial comparisons, breakdowns, and allocations using clean Markdown tables, structured bullet points, and bold section headers.\n"
            "6. TOPIC RELEVANCE & FOCUS:\n"
            "   - When the user explicitly asks you to focus on specific topics (e.g. Gold, Bank Certificates, Liquid Cash), answer ONLY about those requested topics.\n"
            "   - DO NOT summarize or report on unrequested background modules (such as employee salary entries or company payments) when the user specifies a particular focus area.\n"
            "7. Keep responses concise, professional, accurate, and visually structured."
        )

        from core.services.ai.knowledge_engine import AIKnowledgeEngine
        knowledge_context = AIKnowledgeEngine.build_knowledge_context(user=user, query=query)

        return f"{base_prompt}{guardrails}{knowledge_context}"

    def summarize_payload(self, service_key: str, payload: dict[str, Any]) -> str:
        """
        Formats a service payload into compact, readable Markdown for AI context.
        """
        if not payload:
            return f"### {service_key.replace('_', ' ').title()}\nNo data available.\n"

        lines = [f"### {service_key.replace('_', ' ').title()} Payload Data:"]
        try:
            compact_json = json.dumps(payload, default=str, ensure_ascii=False, indent=2)
            lines.append(compact_json)
        except Exception:
            lines.append(str(payload))

        return "\n".join(lines) + "\n"

    def assemble_messages(
        self,
        user_query: str,
        history_messages: Sequence[AIMessage] | None = None,
        user: Any = None,
    ) -> tuple[list[dict[str, str]], list[str]]:
        """
        Assembles message list for the AI provider along with source service names.
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

        service_keys = self.determine_relevant_services(user_query)

        # 1. Gather System Instruction (Priority 1 & 2)
        system_instruction = self.build_system_prompt(user=user, query=user_query)
        current_chars = len(system_instruction) + 50

        # 2. Separate Payload Data into High-Priority Summaries vs Low-Priority Timelines
        high_priority_blocks = []
        low_priority_blocks = []
        sources = []

        for key in service_keys:
            payload = get_financial_advisor_payload(key)
            if not payload:
                continue

            sources.append(key)
            if isinstance(payload, dict):
                # Separate summary from raw items/timelines if present
                summary_part = {k: v for k, v in payload.items() if k not in {"items", "recent_monthly_timeline", "recent_expenses"}}
                detail_part = {k: v for k, v in payload.items() if k in {"items", "recent_monthly_timeline", "recent_expenses"}}

                if summary_part:
                    high_priority_blocks.append(self.summarize_payload(f"{key}_summary", summary_part))
                if detail_part:
                    low_priority_blocks.append(self.summarize_payload(f"{key}_details", detail_part))
            else:
                high_priority_blocks.append(self.summarize_payload(key, payload))

        # 3. Assemble System Context String safely within token budget
        context_parts = []
        for block in high_priority_blocks:
            if current_chars + len(block) <= max_chars:
                context_parts.append(block)
                current_chars += len(block)

        # Append degradable low priority blocks section-by-section cleanly
        for block in low_priority_blocks:
            if current_chars + len(block) <= max_chars:
                context_parts.append(block)
                current_chars += len(block)
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
