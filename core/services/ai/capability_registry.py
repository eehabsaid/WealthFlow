"""
Automatic Capability Registry for AI Architecture Subsystem.
Discovers and aggregates functional business capabilities across data providers, services, models, and views.
CRITICAL CONSTRAINT: 100% READ-ONLY. Zero DB write calls.
"""

from __future__ import annotations

import logging
from typing import Any
from core.services.ai.providers.registry import autodiscover_providers

logger = logging.getLogger(__name__)

_STATIC_CAPABILITIES: list[dict[str, Any]] = [
    {
        "name": "Portfolio Optimization & Allocation Health",
        "provided_by": "PortfolioOptimizerService",
        "consumes": ["BalanceEntry", "BankCertificate", "FixedAsset", "GoldPrice"],
        "used_by": ["Portfolio Optimizer Tab", "Financial Advisor Overview"],
        "inputs": ["asset_allocation", "risk_tolerance"],
        "outputs": ["health_score", "diversification_score", "allocation_cards", "rebalance_recommendations"],
        "description": "Calculates portfolio health score and asset class allocation targets against recommended benchmarks.",
    },
    {
        "name": "Opportunity Detection Engine",
        "provided_by": "OpportunityDetectionService",
        "consumes": ["BankCertificate", "GoldPrice", "BalanceEntry", "Expense"],
        "used_by": ["Opportunity Detection Tab", "AI Advisor"],
        "inputs": ["yield_rates", "idle_cash_threshold"],
        "outputs": ["opportunity_alerts", "expected_yield_boost"],
        "description": "Scans portfolio for idle cash, maturing certificates, or gold price shifts to suggest high-yield optimizations.",
    },
    {
        "name": "Wealth Growth & Net Worth Forecasting",
        "provided_by": "WealthGrowthForecastService",
        "consumes": ["SalaryEntry", "BalanceEntry", "FixedAsset", "BankCertificate"],
        "used_by": ["Wealth Growth Forecast Tab", "Dashboard"],
        "inputs": ["forecast_horizon_years", "cagr"],
        "outputs": ["projected_net_worth", "cagr_3y", "asset_growth_sparkline"],
        "description": "Projects 1-year and 3-year net worth trajectories and compound annual growth rates.",
    },
    {
        "name": "What-If Scenario Simulation & Event Engine",
        "provided_by": "WhatIfSimulatorService",
        "consumes": ["Scenario", "ScenarioEvent"],
        "used_by": ["What-If Simulator Tab", "Scenario Planner"],
        "inputs": ["scenario_id", "simulated_events"],
        "outputs": ["baseline_vs_scenario_diff", "cash_flow_impact", "debt_impact"],
        "description": "Simulates major life events (house, car, marriage, job loss) to compare financial impact against baseline.",
    },
]


class CapabilityRegistry:
    _capabilities_cache: list[dict[str, Any]] = []

    @classmethod
    def autodiscover(cls) -> list[dict[str, Any]]:
        """
        Dynamically aggregates capabilities declared by all autodiscovered data providers
        plus core static capability definitions.
        """
        providers = autodiscover_providers()
        discovered: list[dict[str, Any]] = list(_STATIC_CAPABILITIES)

        for p_key, provider in providers.items():
            try:
                caps = provider.get_capabilities()
                if isinstance(caps, list):
                    discovered.extend(caps)
            except Exception as exc:
                logger.warning("Failed to collect capabilities from provider '%s': %s", p_key, exc)

        cls._capabilities_cache = discovered
        return cls._capabilities_cache

    @classmethod
    def get_capabilities(cls, search_term: str = "", capability_name: str = "") -> dict[str, Any]:
        """Query capabilities registry with optional search filters."""
        if not cls._capabilities_cache:
            cls.autodiscover()

        caps = cls._capabilities_cache
        term = str(search_term or "").strip().lower()
        c_name = str(capability_name or "").strip().lower()

        if c_name:
            caps = [c for c in caps if c_name in c.get("name", "").lower()]

        if term:
            matched = []
            for c in caps:
                txt = (
                    f"{c.get('name', '')} {c.get('provided_by', '')} "
                    f"{' '.join(c.get('consumes', []))} {' '.join(c.get('used_by', []))} "
                    f"{c.get('description', '')}"
                ).lower()
                if term in txt:
                    matched.append(c)
            caps = matched

        return {
            "total_capabilities_registered": len(cls._capabilities_cache),
            "matching_results_count": len(caps),
            "search_term": term,
            "capabilities": caps,
        }
