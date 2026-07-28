from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Tuple

from core.models import SalaryEntry
from core.services.balance.net_worth_service import NetWorthService
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.goal_planning_service import GoalPlanningService


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0

@dataclass
class RiskMetric:
    id: str
    label_key: str
    score: float
    level: str
    level_key: str
    reason_key: str
    reason_params: dict

class RiskAnalysisService:
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

    def _determine_level(self, score: float) -> Tuple[str, str]:
        if score <= 33.33:
            return "low", "risk_analysis_level_low"
        if score <= 66.66:
            return "moderate", "risk_analysis_level_moderate"
        return "high", "risk_analysis_level_high"

    def _calc_liquidity_risk(self, comp: dict) -> Tuple[float, str, dict]:
        if self._monthly_expenses_override is not None:
            monthly_expenses = max(0.0, self._monthly_expenses_override)
        else:
            monthly_expenses = self._optimizer_service._monthly_expense_average()
        cash_val = _to_float(comp.get("allocation_values", {}).get("type_cash"))
        cert_val = _to_float(comp.get("allocation_values", {}).get("bank_certificates"))
        liquid_value = cash_val + cert_val
        months = self._optimizer_service._emergency_fund_months(liquid_value, monthly_expenses)
        
        if months >= self.EMERGENCY_FUND_TARGET_MONTHS:
            return 5.0, "risk_analysis_reason_liq_good", {"months": str(round(months, 1))}
        if months >= 3.0:
            score = 30.0 + ((self.EMERGENCY_FUND_TARGET_MONTHS - months) / 3.0) * 30.0
            return score, "risk_analysis_reason_liq_mod", {"months": str(round(months, 1))}
        
        score = 60.0 + ((3.0 - months) / 3.0) * 40.0
        return score, "risk_analysis_reason_liq_high", {"months": str(round(months, 1))}

    def _calc_bank_concentration_risk(self, comp: dict) -> Tuple[float, str, dict]:
        bank_exposure = self._optimizer_service._bank_exposure(comp)
        if not bank_exposure:
            return 5.0, "risk_analysis_reason_bank_none", {}
        total_bank_value = sum(b["value"] for b in bank_exposure)
        if total_bank_value <= 0:
            return 5.0, "risk_analysis_reason_bank_none", {}
            
        max_bank_value = bank_exposure[0]["value"]
        pct = max_bank_value / total_bank_value
        
        if pct <= self.BANK_CONCENTRATION_THRESHOLD:
            return 10.0, "risk_analysis_reason_bank_good", {}
        
        score = 20.0 + ((pct - self.BANK_CONCENTRATION_THRESHOLD) / (1.0 - self.BANK_CONCENTRATION_THRESHOLD)) * 80.0
        reason_key = "risk_analysis_reason_bank_high" if pct > 0.50 else "risk_analysis_reason_bank_mod"
        return min(100.0, score), reason_key, {"pct": str(round(pct * 100))}

    def _calc_fixed_asset_concentration_risk(self, comp: dict) -> Tuple[float, str, dict]:
        alloc_vals = comp.get("allocation_values", {})
        assets = [
            _to_float(alloc_vals.get("type_real_estate")),
            _to_float(alloc_vals.get("type_gold")),
            _to_float(alloc_vals.get("type_vehicles")),
            _to_float(alloc_vals.get("type_other_assets")),
        ]
        total_assets = sum(assets)
        if total_assets <= 0:
            return 5.0, "risk_analysis_reason_asset_none", {}
            
        max_asset = max(assets)
        pct = max_asset / total_assets
        
        if pct <= self.ASSET_CONCENTRATION_THRESHOLD:
            return 10.0, "risk_analysis_reason_asset_good", {}
            
        score = 20.0 + ((pct - self.ASSET_CONCENTRATION_THRESHOLD) / (1.0 - self.ASSET_CONCENTRATION_THRESHOLD)) * 80.0
        reason_key = "risk_analysis_reason_asset_high" if pct > 0.60 else "risk_analysis_reason_asset_mod"
        return min(100.0, score), reason_key, {"pct": str(round(pct * 100))}

    def _calc_currency_exposure_risk(self, comp: dict) -> Tuple[float, str, dict]:
        currency_exposure = self._optimizer_service._currency_exposure(comp)
        if not currency_exposure:
            return 5.0, "risk_analysis_reason_curr_none", {}
        total_currency = sum(c["value"] for c in currency_exposure)
        if total_currency <= 0:
            return 5.0, "risk_analysis_reason_curr_none", {}
            
        max_curr = currency_exposure[0]["value"]
        pct = max_curr / total_currency
        
        if pct <= self.CURRENCY_CONCENTRATION_THRESHOLD:
            return 15.0, "risk_analysis_reason_curr_good", {}
            
        score = 20.0 + ((pct - self.CURRENCY_CONCENTRATION_THRESHOLD) / (1.0 - self.CURRENCY_CONCENTRATION_THRESHOLD)) * 80.0
        reason_key = "risk_analysis_reason_curr_high" if pct > 0.80 else "risk_analysis_reason_curr_mod"
        return min(100.0, score), reason_key, {"pct": str(round(pct * 100))}

    def _calc_income_stability_risk(self, income_sources: List[dict]) -> Tuple[float, str, dict]:
        from core.services.financial_advisor.risk_analysis_calculations import calc_income_stability_risk
        return calc_income_stability_risk(income_sources)

    def _calc_goal_completion_risk(self) -> Tuple[float, str, dict]:
        goal_payload = self._goal_service.payload()
        summary = goal_payload.get("summary", {})
        total_goals = summary.get("total_goals", 0)
        at_risk_goals = summary.get("at_risk_goals", 0)
        overall_progress = summary.get("overall_progress_pct", 0.0)
        
        if total_goals == 0:
            return 5.0, "risk_analysis_reason_goal_none", {}
            
        progress_risk = 100.0 - overall_progress
        at_risk_pct = (at_risk_goals / total_goals) * 100.0
        
        risk = (progress_risk * 0.4) + (at_risk_pct * 0.6)
        
        if risk <= 33:
            reason = "risk_analysis_reason_goal_good"
        elif risk <= 66:
            reason = "risk_analysis_reason_goal_mod"
        else:
            reason = "risk_analysis_reason_goal_high"
            
        return min(100.0, risk), reason, {"pct": str(round(overall_progress))}

    def _gather_income_sources(self) -> List[dict]:
        sources = []

        if self._salary_override is not None:
            salary_value = max(0.0, self._salary_override)
        else:
            latest_salary = SalaryEntry.objects.filter(paid__gt=0).order_by("-year", "-id").first()
            salary_value = _to_float(latest_salary.paid) if latest_salary else 0.0
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

    def _generate_findings(self, metrics: Dict[str, RiskMetric], comp: dict, income_sources: List[dict]) -> List[dict]:
        findings = []
        
        if metrics["bank"].score >= 50:
            bank_exposure = self._optimizer_service._bank_exposure(comp)
            largest_bank = bank_exposure[0]["bank_name"] if bank_exposure else "one bank"
            findings.append({
                "severity": "high",
                "severity_key": "risk_analysis_severity_high",
                "title_key": "risk_analysis_finding_bank_conc_title",
                "title_params": {"bank": largest_bank},
                "desc_key": "risk_analysis_finding_bank_conc_desc"
            })
            
        monthly_expenses = self._optimizer_service._monthly_expense_average()
        liquid_value = _to_float(comp.get("allocation_values", {}).get("type_cash")) + _to_float(comp.get("allocation_values", {}).get("bank_certificates"))
        months = self._optimizer_service._emergency_fund_months(liquid_value, monthly_expenses)
        if months < self.EMERGENCY_FUND_TARGET_MONTHS:
            findings.append({
                "severity": "medium",
                "severity_key": "risk_analysis_severity_medium",
                "title_key": "risk_analysis_finding_liquidity_title",
                "title_params": {"months": str(round(months, 1))},
                "desc_key": "risk_analysis_finding_liquidity_desc"
            })
        else:
            findings.append({
                "severity": "low",
                "severity_key": "risk_analysis_severity_low",
                "title_key": "risk_analysis_finding_liquidity_good_title",
                "title_params": {"months": str(round(months, 1))},
                "desc_key": "risk_analysis_finding_liquidity_good_desc"
            })
            
        if metrics["asset"].score >= 50:
            alloc_vals = comp.get("allocation_values", {})
            assets = {
                "Real Estate": _to_float(alloc_vals.get("type_real_estate")),
                "Gold": _to_float(alloc_vals.get("type_gold")),
                "Vehicles": _to_float(alloc_vals.get("type_vehicles")),
            }
            if sum(assets.values()) > 0:
                top_asset_name = max(assets.items(), key=lambda x: x[1])[0]
                pct = round((assets[top_asset_name] / sum(assets.values())) * 100.0)
                findings.append({
                    "severity": "info",
                    "severity_key": "risk_analysis_severity_info",
                    "title_key": "risk_analysis_finding_asset_conc_title",
                    "title_params": {"asset": top_asset_name, "pct": str(pct)},
                    "desc_key": "risk_analysis_finding_asset_conc_desc"
                })
                
        if metrics["currency"].score <= 40:
            findings.append({
                "severity": "low",
                "severity_key": "risk_analysis_severity_low",
                "title_key": "risk_analysis_finding_currency_good_title",
                "title_params": {},
                "desc_key": "risk_analysis_finding_currency_good_desc"
            })
            
        if len(income_sources) >= 2:
            findings.append({
                "severity": "low",
                "severity_key": "risk_analysis_severity_low",
                "title_key": "risk_analysis_finding_income_good_title",
                "title_params": {"count": str(len(income_sources))},
                "desc_key": "risk_analysis_finding_income_good_desc"
            })
            
        return findings[:5]

    def _stress_tests(self, comp: dict) -> List[dict]:
        total_nw = _to_float(comp.get("net_worth_egp"))
        if total_nw <= 0:
            return []
            
        alloc_vals = comp.get("allocation_values", {})
        gold_val = _to_float(alloc_vals.get("type_gold"))
        real_estate_val = _to_float(alloc_vals.get("type_real_estate"))
        
        rates = comp.get("rates", {})
        foreign_val = 0.0
        totals_by_currency = comp.get("totals_by_currency", {})
        for code, amount in totals_by_currency.items():
            if str(code).upper() not in ("EGP", "GOLD"):
                foreign_val += _to_float(amount) * _to_float(rates.get(str(code).upper(), 1.0))
                
        scenarios = [
            {
                "id": "usd_up",
                "icon": "bi-currency-dollar",
                "title_key": "risk_analysis_stress_usd_title",
                "desc_key": "risk_analysis_stress_usd_desc",
                "impact_amount": foreign_val * 0.20,
            },
            {
                "id": "gold_down",
                "icon": "bi-coin",
                "title_key": "risk_analysis_stress_gold_title",
                "desc_key": "risk_analysis_stress_gold_desc",
                "impact_amount": gold_val * -0.15,
            },
            {
                "id": "real_estate_down",
                "icon": "bi-house-door",
                "title_key": "risk_analysis_stress_re_title",
                "desc_key": "risk_analysis_stress_re_desc",
                "impact_amount": real_estate_val * -0.10,
            }
        ]
        
        salary_source = SalaryEntry.objects.filter(paid__gt=0).order_by("-year", "-id").first()
        if salary_source:
            salary_annual_impact = _to_float(salary_source.paid) * 6 * -1.0 # 6 months loss
            scenarios.append({
                "id": "salary_down",
                "icon": "bi-briefcase",
                "title_key": "risk_analysis_stress_salary_title",
                "desc_key": "risk_analysis_stress_salary_desc",
                "impact_amount": salary_annual_impact,
            })
            
        for sc in scenarios:
            sc["impact_pct"] = round((sc["impact_amount"] / total_nw) * 100.0, 1)
            sc["impact_amount"] = round(sc["impact_amount"], 2)
            
        return scenarios

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
