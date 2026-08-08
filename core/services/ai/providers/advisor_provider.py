"""
Financial Advisor Payload Provider for AI business context. Read-only.
"""

from __future__ import annotations

from typing import Any
from core.services.ai.providers.base import BaseContextProvider
from core.services.financial_advisor.registry import get_financial_advisor_payload


class FinancialAdvisorDataProvider(BaseContextProvider):
    @property
    def key(self) -> str:
        return "financial_advisor"

    @property
    def name(self) -> str:
        return "Financial Advisor Engine Insights"

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [{
            "name": "Financial Health & Opportunity Engine",
            "provided_by": "FinancialAdvisorDataProvider",
            "consumes": ["FinancialAdvisorOverviewService", "OpportunityDetectionService"],
            "used_by": ["Financial Advisor Dashboard", "AI Assistant"],
            "inputs": ["service_key"],
            "outputs": ["overview", "opportunity_detection"],
            "description": "Provides financial health score, alerts, KPIs, cash flow forecast, and opportunity detection.",
        }]

    def get_data(self, user: Any, limit: int | None = None) -> dict[str, Any]:
        return {
            "overview": get_financial_advisor_payload("overview"),
            "opportunity_detection": get_financial_advisor_payload("opportunity_detection"),
        }
