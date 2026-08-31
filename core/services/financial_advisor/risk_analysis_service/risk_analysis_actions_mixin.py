"""
NOTE: Part of the risk_analysis_service package (split per the >200-line rule).
RiskActionsMixin turns finalized metric scores into a ranked action list and a
single top-line recommendation. Reads metrics only; never mutates them
(metrics-first, recommendations-second).
"""
from __future__ import annotations

from typing import Dict, List

from core.services.financial_advisor.risk_analysis_service.metrics import RiskMetric


class RiskActionsMixin:
    def _generate_priority_actions(self, metrics: Dict[str, RiskMetric]) -> List[dict]:
        actions = []
        sorted_metrics = sorted(metrics.values(), key=lambda m: m.score, reverse=True)

        for metric in sorted_metrics:
            if metric.id == "bank" and metric.score > 40:
                actions.append({
                    "title_key": "risk_analysis_action_diversify_certs",
                    "desc_key": "risk_analysis_action_diversify_certs_desc",
                    "impact": "High",
                    "impact_key": "risk_analysis_impact_high",
                    "difficulty": "Easy",
                    "difficulty_key": "risk_analysis_diff_easy",
                    "improvement": round(metric.score * self.WEIGHTS["bank"], 1)
                })
            elif metric.id == "liquidity" and metric.score > 40:
                actions.append({
                    "title_key": "risk_analysis_action_emergency_fund",
                    "desc_key": "risk_analysis_action_emergency_fund_desc",
                    "impact": "High",
                    "impact_key": "risk_analysis_impact_high",
                    "difficulty": "Medium",
                    "difficulty_key": "risk_analysis_diff_medium",
                    "improvement": round(metric.score * self.WEIGHTS["liquidity"], 1)
                })
            elif metric.id == "goal" and metric.score > 50:
                actions.append({
                    "title_key": "risk_analysis_action_goal_contributions",
                    "desc_key": "risk_analysis_action_goal_contributions_desc",
                    "impact": "Medium",
                    "impact_key": "risk_analysis_impact_medium",
                    "difficulty": "Easy",
                    "difficulty_key": "risk_analysis_diff_easy",
                    "improvement": round(metric.score * self.WEIGHTS["goal"], 1)
                })
            elif metric.id == "asset" and metric.score > 60:
                actions.append({
                    "title_key": "risk_analysis_action_rebalance_assets",
                    "desc_key": "risk_analysis_action_rebalance_assets_desc",
                    "impact": "High",
                    "impact_key": "risk_analysis_impact_high",
                    "difficulty": "Hard",
                    "difficulty_key": "risk_analysis_diff_hard",
                    "improvement": round((metric.score - 20) * self.WEIGHTS["asset"], 1)
                })
            elif metric.id == "income" and metric.score > 50:
                actions.append({
                    "title_key": "risk_analysis_action_income_sources",
                    "desc_key": "risk_analysis_action_income_sources_desc",
                    "impact": "Medium",
                    "impact_key": "risk_analysis_impact_medium",
                    "difficulty": "Hard",
                    "difficulty_key": "risk_analysis_diff_hard",
                    "improvement": round(metric.score * self.WEIGHTS["income"], 1)
                })

        actions.sort(key=lambda a: a["improvement"], reverse=True)
        for i, action in enumerate(actions):
            action["priority_num"] = i + 1

        return actions[:4]

    def _generate_overall_recommendation(self, score: float, actions: List[dict]) -> dict:
        level, level_key = self._determine_level(score)
        top_action = actions[0] if actions else None

        return {
            "score_desc_key": f"risk_analysis_overall_{level}",
            "top_action_title_key": top_action["title_key"] if top_action else "risk_analysis_overall_no_action_title",
            "top_action_desc_key": top_action["desc_key"] if top_action else "risk_analysis_overall_no_action_desc"
        }
