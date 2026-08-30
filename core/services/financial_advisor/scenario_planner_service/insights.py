"""Rule-based comparative financial insights mixin for ScenarioPlannerService.

NOTE (200-line file convention): extracted from the original monolithic
core/services/financial_advisor/scenario_planner_service.py (716 lines).
See __init__.py for the full package layout.
"""
from __future__ import annotations

from typing import List

from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService

from .config import _to_float


class InsightsMixin:
    """Provides generate_insights(); mixed into ScenarioPlannerService."""

    def generate_insights(self, baseline: dict, scenario_data: dict) -> List[dict]:
        """Generates rule-based financial insights comparing scenario vs baseline.

        Uses SCENARIO_PLANNER_CONFIG threshold constants for warnings/good news.
        """
        insights: List[dict] = []

        emer_min = _to_float(self.config.get("EMERGENCY_FUND_MIN_MONTHS", 3.0))
        base_cov = _to_float(baseline.get("cash_coverage_months"))
        scen_cov = _to_float(scenario_data.get("cash_coverage_months"))

        # 1. Emergency Fund drop below safe threshold
        if scen_cov < emer_min and base_cov >= emer_min:
            insights.append({
                "severity": "bad",
                "title_key": "scenario_planner_insight_emer_fund_low_title",
                "body_key": "scenario_planner_insight_emer_fund_low_body",
                "params": {"months": str(scen_cov), "min": str(emer_min)},
                "impact_text": f"Cash coverage drops to {scen_cov} months (below the {emer_min}-month minimum safety buffer).",
                "action_text": "Consider staging down payments or building liquidity before executing major capital outflows.",
                "alternative_text": "Alternative: Extend loan tenure or utilize certificate interest liquidity to cushion cash reserves.",
            })
        elif scen_cov < base_cov and scen_cov >= emer_min:
            insights.append({
                "severity": "warn",
                "title_key": "scenario_planner_insight_emer_fund_reduced_title",
                "body_key": "scenario_planner_insight_emer_fund_reduced_body",
                "params": {"months": str(scen_cov)},
                "impact_text": f"Liquidity buffer is reduced from {base_cov} to {scen_cov} months of expenses.",
                "action_text": "Monitor monthly surplus to ensure unexpected expenses can still be absorbed smoothly.",
                "alternative_text": "Alternative: Allocate a portion of monthly cash surplus directly to high-yield liquid reserves.",
            })

        # 2. Goal probability drop
        base_goal_pct = _to_float(baseline.get("goal_achievement_pct"))
        scen_goal_pct = _to_float(scenario_data.get("goal_achievement_pct"))
        goal_drop_limit = _to_float(self.config.get("GOAL_PROBABILITY_DROP_THRESHOLD_PCT", 10.0))

        if (base_goal_pct - scen_goal_pct) >= goal_drop_limit:
            insights.append({
                "severity": "warn",
                "title_key": "scenario_planner_insight_goal_risk_title",
                "body_key": "scenario_planner_insight_goal_risk_body",
                "params": {"drop_pt": str(round(base_goal_pct - scen_goal_pct, 1))},
                "impact_text": f"Goal achievement probability decreases by {round(base_goal_pct - scen_goal_pct, 1)}%.",
                "action_text": "Re-evaluate non-essential goal target dates or adjust monthly contribution targets.",
                "alternative_text": "Alternative: Re-invest maturing certificate principal directly into target goal allocations.",
            })

        # 3. Gold allocation band check
        gold_band = PortfolioOptimizerService.RECOMMENDED_BANDS.get("gold")
        gold_min = gold_band.min_pct if gold_band else 10.0
        scen_gold_pct = _to_float(scenario_data.get("gold_allocation_pct"))
        if 0 < scen_gold_pct < gold_min:
            insights.append({
                "severity": "warn",
                "title_key": "scenario_planner_insight_gold_low_title",
                "body_key": "scenario_planner_insight_gold_low_body",
                "params": {"pct": str(scen_gold_pct), "min": str(gold_min)},
                "impact_text": f"Gold allocation drops to {scen_gold_pct}% (recommended band is {gold_min}%–20%).",
                "action_text": "Maintain minimum gold allocation to preserve portfolio inflation protection.",
                "alternative_text": "Alternative: Liquidate secondary cash accounts instead of gold reserves.",
            })

        # 4. Debt increase notice
        base_debt = _to_float(baseline.get("total_debt"))
        scen_debt = _to_float(scenario_data.get("total_debt"))
        if scen_debt > base_debt:
            debt_diff = scen_debt - base_debt
            insights.append({
                "severity": "warn",
                "title_key": "scenario_planner_insight_debt_added_title",
                "body_key": "scenario_planner_insight_debt_added_body",
                "params": {"added_debt": str(round(debt_diff, 2))},
                "impact_text": f"New liabilities of +{round(debt_diff, 2):,} EGP added to your balance sheet.",
                "action_text": "Ensure your debt-to-income ratio remains under 40% to maintain financial flexibility.",
                "alternative_text": "Alternative: Increase initial down payment to lower total interest expenses over time.",
            })

        # 5. Net worth positive growth despite events
        base_nw = _to_float(baseline.get("net_worth_12m"))
        scen_nw = _to_float(scenario_data.get("net_worth_12m"))
        if scen_nw > base_nw:
            nw_diff = scen_nw - base_nw
            insights.append({
                "severity": "good",
                "title_key": "scenario_planner_insight_nw_growth_title",
                "body_key": "scenario_planner_insight_nw_growth_body",
                "params": {"diff": str(round(nw_diff, 2))},
                "impact_text": f"Net worth projects an additional +{round(nw_diff, 2):,} EGP growth over baseline at 12 months.",
                "action_text": "Re-invest projected surplus into diversified yield assets.",
                "alternative_text": "Alternative: Accelerate debt payoff or contribute to long-term goals ahead of schedule.",
            })

        if not insights:
            insights.append({
                "severity": "good",
                "title_key": "scenario_planner_insight_stable_title",
                "body_key": "scenario_planner_insight_stable_body",
                "params": {},
                "impact_text": "Scenario maintains overall financial stability and liquidity reserves.",
                "action_text": "Proceed with planned milestones while keeping regular periodic reviews.",
                "alternative_text": "Alternative: Explore opportunity investments if cash surplus increases.",
            })

        return insights

