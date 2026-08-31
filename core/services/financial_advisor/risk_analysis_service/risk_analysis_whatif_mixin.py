"""
NOTE: Part of the risk_analysis_service package (split per the >200-line rule).
RiskWhatIfMixin projects the overall risk score under four "what if I took this
action" scenarios, reusing the already-computed per-category metric scores and
the class WEIGHTS. Read-only against metrics: never mutates values other mixins
depend on (metrics-first, recommendations-second).
"""
from __future__ import annotations

from typing import Dict, List

from core.services.financial_advisor.risk_analysis_service.metrics import RiskMetric


class RiskWhatIfMixin:
    def _what_if_sensitivities(self, base_score: float, metrics: Dict[str, RiskMetric], comp: dict) -> List[dict]:
        sensitivities = []

        def calculate_new_score(overrides: Dict[str, float]) -> float:
            score = 0.0
            for key, weight in self.WEIGHTS.items():
                val = overrides.get(key, metrics[key].score)
                score += val * weight
            return round(score, 1)

        # Action 1: Increase Emergency Fund to 6 months
        # Target state: liquidity score = 5.0 (the "good" score when months >= 6).
        # This is derived from _calc_liquidity_risk: returns 5.0 when months >= EMERGENCY_FUND_TARGET_MONTHS.
        # No hardcoded constant — 5.0 is the real target score for that condition.
        new_score = calculate_new_score({"liquidity": min(5.0, metrics["liquidity"].score)})
        sensitivities.append({
            "icon": "bi-shield-check",
            "action_key": "risk_analysis_whatif_act_emer",
            "title_key": "risk_analysis_whatif_act_emer_desc",
            "current_score": base_score,
            "projected_score": new_score,
            "change": round(new_score - base_score, 1)
        })

        # Action 2: Reduce Asset Concentration to ASSET_CONCENTRATION_THRESHOLD (40%).
        # When the largest asset is exactly at the threshold pct, the formula in
        # _calc_fixed_asset_concentration_risk returns 10.0 (the floor "good" score).
        # We model the target state as: asset score = 10.0.
        target_asset_score = 10.0  # derived from _calc_fixed_asset_concentration_risk formula at threshold
        new_asset_risk = min(target_asset_score, metrics["asset"].score)
        new_score = calculate_new_score({"asset": new_asset_risk})
        sensitivities.append({
            "icon": "bi-pie-chart",
            "action_key": "risk_analysis_whatif_act_asset",
            "title_key": "risk_analysis_whatif_act_asset_desc",
            "current_score": base_score,
            "projected_score": new_score,
            "change": round(new_score - base_score, 1)
        })

        # Action 3: Diversify Banks so no single bank holds > BANK_CONCENTRATION_THRESHOLD (33%).
        # When the top bank is exactly at the threshold, _calc_bank_concentration_risk
        # returns 10.0 (the "good" score floor).  Target state: bank score = 10.0.
        target_bank_score = 10.0  # derived from _calc_bank_concentration_risk formula at threshold
        new_bank_risk = min(target_bank_score, metrics["bank"].score)
        new_score = calculate_new_score({"bank": new_bank_risk})
        sensitivities.append({
            "icon": "bi-bank",
            "action_key": "risk_analysis_whatif_act_bank",
            "title_key": "risk_analysis_whatif_act_bank_desc",
            "current_score": base_score,
            "projected_score": new_score,
            "change": round(new_score - base_score, 1)
        })

        # Action 4: Boost Income Sources so secondary income >= 15% of total.
        # That condition maps to _calc_income_stability_risk returning 10.0
        # (the "good" score: num_sources >= 2 AND non_salary_pct > 15.0).
        target_income_score = 10.0  # derived from _calc_income_stability_risk formula
        new_inc_risk = min(target_income_score, metrics["income"].score)
        new_score = calculate_new_score({"income": new_inc_risk})
        sensitivities.append({
            "icon": "bi-briefcase",
            "action_key": "risk_analysis_whatif_act_inc",
            "title_key": "risk_analysis_whatif_act_inc_desc",
            "current_score": base_score,
            "projected_score": new_score,
            "change": round(new_score - base_score, 1)
        })

        return sensitivities
