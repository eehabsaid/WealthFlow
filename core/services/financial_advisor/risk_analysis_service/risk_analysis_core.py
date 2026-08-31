"""
NOTE: Part of the risk_analysis_service package (split per the >200-line rule).
RiskAnalysisService assembles the calc/findings/whatif/actions mixins, owns the
constructor, collaborator services, shared _determine_level, income-source
gathering, and the payload() orchestration entry point.
"""
from __future__ import annotations

from datetime import date

from core.services.balance.net_worth_service import NetWorthService
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.goal_planning_service import GoalPlanningService

from core.services.financial_advisor.risk_analysis_service.metrics import RiskMetric, _to_float
from core.services.financial_advisor.risk_analysis_service.risk_analysis_calc_mixin import RiskCalcMixin
from core.services.financial_advisor.risk_analysis_service.risk_analysis_findings_mixin import RiskFindingsMixin
from core.services.financial_advisor.risk_analysis_service.risk_analysis_whatif_mixin import RiskWhatIfMixin
from core.services.financial_advisor.risk_analysis_service.risk_analysis_actions_mixin import RiskActionsMixin


class RiskAnalysisService(RiskCalcMixin, RiskFindingsMixin, RiskWhatIfMixin, RiskActionsMixin):
    # ── Configuration Constants ─────────────────────────────────────────────
    EMERGENCY_FUND_TARGET_MONTHS = 6.0
    BANK_CONCENTRATION_THRESHOLD = 0.33
    ASSET_CONCENTRATION_THRESHOLD = 0.40
    CURRENCY_CONCENTRATION_THRESHOLD = 0.50

    WEIGHTS = {
        "liquidity": 0.25,
        "bank": 0.15,
        "asset": 0.15,
        "currency": 0.15,
        "income": 0.15,
        "goal": 0.15,
    }

    def __init__(self, today: date | None = None, net_worth_service: NetWorthService | None = None,
                 salary_override: float | None = None,
                 monthly_expenses_override: float | None = None):
        self.today = today or date.today()
        self._net_worth_service = net_worth_service or NetWorthService()
        self._optimizer_service = PortfolioOptimizerService(
            today=self.today,
            net_worth_service=self._net_worth_service,
            monthly_expenses_override=monthly_expenses_override,
        )
        self._goal_service = GoalPlanningService(today=self.today)
        self._salary_override = salary_override
        self._monthly_expenses_override = monthly_expenses_override

    def _determine_level(self, score: float):
        if score <= 33.33:
            return "low", "risk_analysis_level_low"
        if score <= 66.66:
            return "moderate", "risk_analysis_level_moderate"
        return "high", "risk_analysis_level_high"

    def _gather_income_sources(self) -> list[dict]:
        sources = []

        if self._salary_override is not None:
            salary_value = max(0.0, self._salary_override)
        else:
            from core.services.salary.salary_service import get_current_monthly_salary
            salary_value = get_current_monthly_salary()
        if salary_value > 0:
            sources.append({"id": "salary", "label_key": "risk_analysis_income_salary", "value": salary_value})

        comp = self._net_worth_service.portfolio_components()
        cert_interest = _to_float(comp.get("certificate_interest_total_egp"))
        if cert_interest > 0:
            sources.append({"id": "certificate", "label_key": "risk_analysis_income_certificates", "value": cert_interest})

        total = sum(s["value"] for s in sources)
        for s in sources:
            s["percentage"] = round((s["value"] / total) * 100.0, 1) if total > 0 else 0.0

        return sorted(sources, key=lambda x: x["value"], reverse=True)

    def payload(self) -> dict:
        comp = self._net_worth_service.portfolio_components()
        optimizer_payload = self._optimizer_service.payload()
        portfolio_health_val = optimizer_payload.get("health", {}).get("score", 100)

        income_sources = self._gather_income_sources()

        v_liq, r_liq, p_liq = self._calc_liquidity_risk(comp)
        v_bnk, r_bnk, p_bnk = self._calc_bank_concentration_risk(comp)
        v_ast, r_ast, p_ast = self._calc_fixed_asset_concentration_risk(comp)
        v_cur, r_cur, p_cur = self._calc_currency_exposure_risk(comp)
        v_inc, r_inc, p_inc = self._calc_income_stability_risk(income_sources)
        v_gol, r_gol, p_gol = self._calc_goal_completion_risk()

        metrics_dict = {
            "liquidity": RiskMetric("liquidity", "risk_analysis_metric_liquidity", v_liq, *self._determine_level(v_liq), r_liq, p_liq),
            "bank": RiskMetric("bank", "risk_analysis_metric_bank", v_bnk, *self._determine_level(v_bnk), r_bnk, p_bnk),
            "asset": RiskMetric("asset", "risk_analysis_metric_asset", v_ast, *self._determine_level(v_ast), r_ast, p_ast),
            "currency": RiskMetric("currency", "risk_analysis_metric_currency", v_cur, *self._determine_level(v_cur), r_cur, p_cur),
            "income": RiskMetric("income", "risk_analysis_metric_income", v_inc, *self._determine_level(v_inc), r_inc, p_inc),
            "goal": RiskMetric("goal", "risk_analysis_metric_goal", v_gol, *self._determine_level(v_gol), r_gol, p_gol),
        }

        # Calculate raw score from weighted categories
        raw_score = sum(m.score * self.WEIGHTS[k] for k, m in metrics_dict.items())

        # Correlate with Portfolio Health to ensure consistency.
        # If health is 89, inverse health is 11. Average them so they complement each other.
        inverse_health = max(0.0, 100.0 - portfolio_health_val)
        total_score = (raw_score * 0.4) + (inverse_health * 0.6)
        total_score = round(total_score, 1)

        score_level, score_level_key = self._determine_level(total_score)

        radar_data = {
            "labels": [m.label_key for m in metrics_dict.values()],
            "values": [round(m.score, 1) for m in metrics_dict.values()]
        }

        income_stability_score = round(max(0.0, 100.0 - v_inc), 1)
        inc_level = "Healthy" if income_stability_score >= 60 else "Moderate" if income_stability_score >= 40 else "Weak"
        inc_level_key = f"risk_analysis_income_level_{inc_level.lower()}"

        actions = self._generate_priority_actions(metrics_dict)
        overall = self._generate_overall_recommendation(total_score, actions)

        return {
            "as_of": self.today.isoformat(),
            "portfolio_health": {
                "score": portfolio_health_val,
                "label_key": optimizer_payload.get("health", {}).get("label_key", ""),
            },
            "risk_score": {
                "score": total_score,
                "level": score_level,
                "level_key": score_level_key,
            },
            "breakdown": [
                {
                    "id": m.id, "label_key": m.label_key, "score": round(m.score, 1),
                    "level": m.level, "level_key": m.level_key,
                    "reason_key": m.reason_key, "reason_params": m.reason_params
                }
                for m in metrics_dict.values()
            ],
            "radar": radar_data,
            "findings": self._generate_findings(metrics_dict, comp, income_sources),
            "stress_tests": self._stress_tests(comp),
            "sensitivities": self._what_if_sensitivities(total_score, metrics_dict, comp),
            "priority_actions": actions,
            "overall_recommendation": overall,
            "income_stability": {
                "score": income_stability_score,
                "level_key": inc_level_key,
                "sources": [s for s in income_sources if s["value"] > 0],
            }
        }
