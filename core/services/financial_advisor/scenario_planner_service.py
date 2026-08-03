"""Financial Scenario Planner Service.

Calculates multi-event financial scenario projections, N-way side-by-side comparison,
rule-based financial insights, and presentation-only retirement readiness.

Architectural Constraints:
1. Reuses existing engines:
   - WealthGrowthForecastService.forecast_with_overrides() for net worth projection series.
   - RiskAnalysisService for risk scoring.
   - GoalPlanningService for goal achievement %.
   - PortfolioOptimizerService.RECOMMENDED_BANDS for asset allocation checks.
   - NetWorthService for current portfolio balances & cash flow baselines.
   - AssetMortgage model for real debt baseline.
2. Retirement readiness is computed strictly as a derived presentation metric from projected net worth.
   It NEVER mutates or interferes with GoalPlanningService, WealthGrowthForecastService, or NetWorthService.
3. Centralized threshold configuration: SCENARIO_PLANNER_CONFIG.
4. Single source of truth for event schema: EVENT_SCHEMA.
5. All calculations wrapped defensively in try/except returning valid JSON.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from core.models import Scenario, ScenarioEvent, AssetMortgage
from core.services.balance.net_worth_service import NetWorthService
from core.services.financial_advisor.wealth_growth_forecast_service import WealthGrowthForecastService
from core.services.financial_advisor.risk_analysis_service import RiskAnalysisService
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.goal_planning_service import GoalPlanningService
from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


# ── Centralized Financial Configuration ───────────────────────────────────────
SCENARIO_PLANNER_CONFIG = {
    "EMERGENCY_FUND_MIN_MONTHS": 3.0,
    "EMERGENCY_FUND_TARGET_MONTHS": 6.0,
    "GOAL_PROBABILITY_DROP_THRESHOLD_PCT": 10.0,
    "DEFAULT_RETIREMENT_AGE": 60,
    "DEFAULT_WITHDRAWAL_RATE": 0.04,
    "NEST_EGG_MULTIPLIER": 25.0,  # 1.0 / 0.04
    "DEBT_TO_INCOME_HIGH_THRESHOLD_PCT": 40.0,
}


# ── Backend Event Schema Registry (Single Source of Truth) ───────────────────
SCENARIO_EVENT_SCHEMA_VERSION = 1

EVENT_SCHEMA = [
    {
        "event_type": "house",
        "label_key": "scenario_planner_event_house",
        "icon": "bi-house-door",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "purchase_price", "label_key": "scenario_planner_field_purchase_price", "type": "number", "default": 3000000, "min": 0},
            {"name": "down_payment", "label_key": "scenario_planner_field_down_payment", "type": "number", "default": 600000, "min": 0},
            {"name": "mortgage_rate_pct", "label_key": "scenario_planner_field_mortgage_rate", "type": "number", "default": 18.0, "min": 0, "max": 100},
            {"name": "term_years", "label_key": "scenario_planner_field_term_years", "type": "number", "default": 20, "min": 1, "max": 40},
            {"name": "monthly_installment", "label_key": "scenario_planner_field_monthly_installment", "type": "number", "default": 35000, "min": 0},
        ],
    },
    {
        "event_type": "car",
        "label_key": "scenario_planner_event_car",
        "icon": "bi-car-front",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "purchase_price", "label_key": "scenario_planner_field_purchase_price", "type": "number", "default": 800000, "min": 0},
            {"name": "down_payment", "label_key": "scenario_planner_field_down_payment", "type": "number", "default": 200000, "min": 0},
            {"name": "monthly_installment", "label_key": "scenario_planner_field_monthly_installment", "type": "number", "default": 15000, "min": 0},
            {"name": "maintenance_monthly", "label_key": "scenario_planner_field_maintenance_monthly", "type": "number", "default": 2000, "min": 0},
        ],
    },
    {
        "event_type": "salary_change",
        "label_key": "scenario_planner_event_salary_change",
        "icon": "bi-graph-up-arrow",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "change_type", "label_key": "scenario_planner_field_change_type", "type": "select", "default": "percentage", "options": ["percentage", "fixed_amount"]},
            {"name": "salary_change_pct", "label_key": "scenario_planner_field_salary_change_pct", "type": "number", "default": 15.0},
            {"name": "salary_change_amount", "label_key": "scenario_planner_field_salary_change_amount", "type": "number", "default": 5000.0},
        ],
    },
    {
        "event_type": "marriage",
        "label_key": "scenario_planner_event_marriage",
        "icon": "bi-heart",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "one_time_cost", "label_key": "scenario_planner_field_one_time_cost", "type": "number", "default": 400000, "min": 0},
            {"name": "new_monthly_expense", "label_key": "scenario_planner_field_new_monthly_expense", "type": "number", "default": 5000, "min": 0},
        ],
    },
    {
        "event_type": "child",
        "label_key": "scenario_planner_event_child",
        "icon": "bi-balloon-heart",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "one_time_cost", "label_key": "scenario_planner_field_one_time_cost", "type": "number", "default": 50000, "min": 0},
            {"name": "new_monthly_expense", "label_key": "scenario_planner_field_new_monthly_expense", "type": "number", "default": 4000, "min": 0},
        ],
    },
    {
        "event_type": "retirement",
        "label_key": "scenario_planner_event_retirement",
        "icon": "bi-umbrella",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "target_age", "label_key": "scenario_planner_field_target_age", "type": "number", "default": 60, "min": 30, "max": 90},
            {"name": "desired_monthly_income", "label_key": "scenario_planner_field_desired_monthly_income", "type": "number", "default": 30000, "min": 0},
        ],
    },
    {
        "event_type": "inheritance",
        "label_key": "scenario_planner_event_inheritance",
        "icon": "bi-gift",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "lump_sum_amount", "label_key": "scenario_planner_field_lump_sum_amount", "type": "number", "default": 1000000, "min": 0},
        ],
    },
    {
        "event_type": "medical",
        "label_key": "scenario_planner_event_medical",
        "icon": "bi-hospital",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "one_time_cost", "label_key": "scenario_planner_field_one_time_cost", "type": "number", "default": 150000, "min": 0},
            {"name": "monthly_ongoing_cost", "label_key": "scenario_planner_field_ongoing_cost", "type": "number", "default": 1500, "min": 0},
        ],
    },
    {
        "event_type": "business",
        "label_key": "scenario_planner_event_business",
        "icon": "bi-briefcase",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "capital_investment", "label_key": "scenario_planner_field_capital_investment", "type": "number", "default": 500000, "min": 0},
            {"name": "monthly_net_profit", "label_key": "scenario_planner_field_monthly_net_profit", "type": "number", "default": 10000},
        ],
    },
    {
        "event_type": "job_loss",
        "label_key": "scenario_planner_event_job_loss",
        "icon": "bi-x-octagon",
        "fields": [
            {"name": "event_date", "label_key": "scenario_planner_field_event_date", "type": "date", "default": ""},
            {"name": "duration_months", "label_key": "scenario_planner_field_duration_months", "type": "number", "default": 6, "min": 1, "max": 36},
        ],
    },
]


class ScenarioPlannerService:
    """Computes projections, comparison, and insights for Scenario Planner."""

    def __init__(self, today: date | None = None, user=None):
        self.today = today or date.today()
        self.user = user
        self.config = dict(SCENARIO_PLANNER_CONFIG)
        self._net_worth_service = NetWorthService()
        self._forecast_service = WealthGrowthForecastService(
            today=self.today,
            net_worth_service=self._net_worth_service,
        )
        self._cash_flow_service = CashFlowForecastService(
            today=self.today,
            net_worth_service=self._net_worth_service,
        )
        self._goal_service = GoalPlanningService(
            today=self.today,
            net_worth_service=self._net_worth_service,
        )

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def _get_current_real_debt(self) -> float:
        """Fetch total real debt from AssetMortgage model."""
        mortgages = AssetMortgage.objects.all()
        rates = self._net_worth_service.portfolio_components().get("rates", {})
        total_debt = 0.0
        for m in mortgages:
            rem = _to_float(m.remaining_balance)
            code = str(m.currency.code if m.currency else "EGP").upper()
            rate = 1.0 if code in ("", "EGP") else _to_float(rates.get(code)) or 1.0
            total_debt += rem * rate
        return total_debt

    def _events_to_overrides(
        self, events: List[ScenarioEvent], monthly_salary: float = 0.0
    ) -> tuple[dict, float, int | None]:
        """Translates a list of ScenarioEvents into WealthGrowthForecastService overrides.

        Returns (overrides_dict, scenario_added_debt, scenario_target_age).
        Reuses existing override keys (monthly_salary_scale, monthly_expense_scale)
        and minimal extended keys (monthly_salary_delta, monthly_expense_delta,
        lump_sum_outflows, lump_sum_inflows).
        """
        salary_scale = 1.0
        salary_delta = 0.0
        expense_delta = 0.0
        lump_outflows: List[dict] = []
        lump_inflows: List[dict] = []
        added_debt = 0.0
        scenario_target_age: int | None = None

        for idx, ev in enumerate(events):
            etype = str(ev.event_type or "").lower()
            p = ev.params or {}
            ev_date = ev.event_date or self.today

            # Calculate month_index (1..12) relative to current month
            m_index = max(1, (ev_date.year - self.today.year) * 12 + (ev_date.month - self.today.month) + 1)
            m_index = min(12, m_index)

            if etype == "house":
                down_pay = _to_float(p.get("down_payment"))
                price = _to_float(p.get("purchase_price"))
                installment = _to_float(p.get("monthly_installment"))
                if down_pay > 0:
                    lump_outflows.append({"month_index": m_index, "amount": down_pay})
                if installment > 0:
                    expense_delta += installment
                if price > down_pay:
                    added_debt += (price - down_pay)

            elif etype == "car":
                down_pay = _to_float(p.get("down_payment"))
                price = _to_float(p.get("purchase_price"))
                installment = _to_float(p.get("monthly_installment"))
                maint = _to_float(p.get("maintenance_monthly"))
                if down_pay > 0:
                    lump_outflows.append({"month_index": m_index, "amount": down_pay})
                if (installment + maint) > 0:
                    expense_delta += (installment + maint)
                if price > down_pay:
                    added_debt += (price - down_pay)

            elif etype == "salary_change":
                change_type = str(p.get("change_type", "percentage"))
                if change_type == "percentage":
                    pct = _to_float(p.get("salary_change_pct"))
                    salary_scale *= (1.0 + pct / 100.0)
                else:
                    amt = _to_float(p.get("salary_change_amount"))
                    salary_delta += amt

            elif etype == "marriage":
                cost = _to_float(p.get("one_time_cost"))
                new_exp = _to_float(p.get("new_monthly_expense"))
                if cost > 0:
                    lump_outflows.append({"month_index": m_index, "amount": cost})
                if new_exp > 0:
                    expense_delta += new_exp

            elif etype == "child":
                cost = _to_float(p.get("one_time_cost"))
                new_exp = _to_float(p.get("new_monthly_expense"))
                if cost > 0:
                    lump_outflows.append({"month_index": m_index, "amount": cost})
                if new_exp > 0:
                    expense_delta += new_exp

            elif etype == "inheritance":
                amt = _to_float(p.get("lump_sum_amount"))
                if amt > 0:
                    lump_inflows.append({"month_index": m_index, "amount": amt})

            elif etype == "medical":
                cost = _to_float(p.get("one_time_cost"))
                ongoing = _to_float(p.get("monthly_ongoing_cost") or p.get("ongoing_cost"))
                if cost > 0:
                    lump_outflows.append({"month_index": m_index, "amount": cost})
                if ongoing > 0:
                    expense_delta += ongoing

            elif etype == "business":
                cap = _to_float(p.get("capital_investment"))
                profit = _to_float(p.get("monthly_net_profit"))
                if cap > 0:
                    lump_outflows.append({"month_index": m_index, "amount": cap})
                salary_delta += profit

            elif etype == "job_loss":
                # Approximation: Lump-sum hit for duration_months of lost salary vs flat global scale-to-zero.
                duration = int(_to_float(p.get("duration_months") or 12))
                duration = max(1, min(duration, 12))
                lost_salary = monthly_salary * duration
                if lost_salary > 0:
                    lump_outflows.append({"month_index": m_index, "amount": lost_salary})

            elif etype == "retirement":
                age_val = _to_float(p.get("target_age"))
                if age_val > 0:
                    scenario_target_age = int(age_val)

        overrides: Dict[str, Any] = {}
        if salary_scale != 1.0:
            overrides["monthly_salary_scale"] = salary_scale
        if salary_delta != 0.0:
            overrides["monthly_salary_delta"] = salary_delta
        if expense_delta != 0.0:
            overrides["monthly_expense_delta"] = expense_delta
        if lump_outflows:
            overrides["lump_sum_outflows"] = lump_outflows
        if lump_inflows:
            overrides["lump_sum_inflows"] = lump_inflows

        return overrides, added_debt, scenario_target_age

    def _compute_retirement_readiness(
        self,
        projected_net_worth_12m: float,
        avg_monthly_expenses: float,
        target_age: int = 60,
    ) -> Dict[str, Any]:
        """Calculates derived presentation-only retirement readiness.

        Formula (standard 4% rule / 25x annual expenses):
            required_nest_egg = (avg_monthly_expenses * 12) * NEST_EGG_MULTIPLIER
            readiness_pct = min(100.0, (projected_net_worth_12m / required_nest_egg) * 100.0)

        This is strictly a display metric — it does NOT alter net worth or forecast.
        """
        nest_egg_multiplier = _to_float(self.config.get("NEST_EGG_MULTIPLIER", 25.0))
        annual_expenses = max(1.0, avg_monthly_expenses * 12.0)
        required_nest_egg = annual_expenses * nest_egg_multiplier

        if required_nest_egg <= 0:
            readiness_pct = 100.0
        else:
            readiness_pct = min(100.0, max(0.0, (projected_net_worth_12m / required_nest_egg) * 100.0))

        return {
            "target_age": target_age,
            "required_nest_egg_egp": round(required_nest_egg, 2),
            "projected_net_worth_egp": round(projected_net_worth_12m, 2),
            "readiness_pct": round(readiness_pct, 1),
            "assumption_note": (
                f"Based on safe withdrawal rate of {int(self.config['DEFAULT_WITHDRAWAL_RATE']*100)}% "
                f"({int(self.config['NEST_EGG_MULTIPLIER'])}x annual expenses of {round(annual_expenses, 2):,} EGP)."
            ),
        }

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

    # ── Public API ────────────────────────────────────────────────────────────

    def payload(self, scenario_ids: List[int] | None = None) -> dict:
        """Computes baseline + requested N scenarios for Scenario Planner tab.

        Parameters
        ----------
        scenario_ids : list[int], optional
            List of Scenario model PKs to compare alongside baseline.
        """
        try:
            cert_forecast = self._net_worth_service.certificate_forecast_payload(today=self.today)
            comp = self._net_worth_service.portfolio_components()

            monthly_salary = _to_float(cert_forecast.get("monthly_salary"))
            monthly_cert_income = _to_float(cert_forecast.get("monthly_certificate_income"))
            monthly_rental_income = _to_float(cert_forecast.get("monthly_rental_income"))
            total_monthly_income = _to_float(cert_forecast.get("total_monthly_income"))
            if total_monthly_income <= 0:
                total_monthly_income = monthly_salary + monthly_cert_income + monthly_rental_income

            avg_monthly_expenses = _to_float(cert_forecast.get("avg_monthly_expenses"))
            cash_balance = _to_float(cert_forecast.get("cash_balance"))
            total_net_worth = _to_float(comp.get("net_worth_egp"))
            gold_value = _to_float(comp.get("gold_value_egp"))
            gold_pct = (gold_value / total_net_worth * 100.0) if total_net_worth > 0 else 0.0
            real_debt_baseline = self._get_current_real_debt()

            baseline_series_data = self._forecast_service.forecast_with_overrides("expected", {})
            baseline_pts = baseline_series_data.get("points", [])
            baseline_nw_12m = baseline_pts[-1]["net_worth"] if baseline_pts else 0.0

            baseline_risk_score = _to_float(
                RiskAnalysisService(today=self.today, net_worth_service=self._net_worth_service)
                .payload()
                .get("risk_score", {})
                .get("score")
            )
            baseline_goal_payload = self._goal_service.payload()
            baseline_goals_list = baseline_goal_payload.get("goals", [])
            if baseline_goals_list:
                unfavorable_statuses = {"at_risk", "critical"}
                favorable_count = sum(1 for g in baseline_goals_list if g.get("status") not in unfavorable_statuses)
                baseline_goal_pct = round((favorable_count / len(baseline_goals_list)) * 100.0, 1)
            else:
                baseline_goal_pct = 100.0

            baseline_coverage = round(cash_balance / avg_monthly_expenses, 1) if avg_monthly_expenses > 0 else None

            baseline_retire = self._compute_retirement_readiness(
                baseline_nw_12m, avg_monthly_expenses, self.config["DEFAULT_RETIREMENT_AGE"]
            )

            baseline_dict = {
                "id": 0,
                "name": "Baseline",
                "description": "Current active financial trajectory",
                "is_baseline_pinned": True,
                "net_worth_12m": round(baseline_nw_12m, 2),
                "monthly_salary": round(monthly_salary, 2),
                "monthly_income": round(total_monthly_income, 2),
                "monthly_expenses": round(avg_monthly_expenses, 2),
                "monthly_cash_flow": round(total_monthly_income - avg_monthly_expenses, 2),
                "total_debt": round(real_debt_baseline, 2),
                "cash_coverage_months": baseline_coverage,
                "risk_score": round(baseline_risk_score, 1),
                "goal_achievement_pct": baseline_goal_pct,
                "gold_allocation_pct": round(gold_pct, 1),
                "retirement_readiness": baseline_retire,
                "series": [
                    {"month_end": pt["month_end"], "net_worth": pt["net_worth"]}
                    for pt in baseline_pts
                ],
                "events": [],
            }

            scenarios_out = []
            if scenario_ids:
                scenarios_qs = (
                    Scenario.objects.filter(id__in=scenario_ids)
                    .prefetch_related("events")
                    .order_by("id")
                )
                for sc in scenarios_qs:
                    events = list(sc.events.all())
                    overrides, added_debt, sc_target_age = self._events_to_overrides(events, monthly_salary=monthly_salary)

                    # Series with scenario overrides
                    sc_series_data = self._forecast_service.forecast_with_overrides("expected", overrides)
                    sc_pts = sc_series_data.get("points", [])
                    sc_nw_12m = sc_pts[-1]["net_worth"] if sc_pts else baseline_nw_12m

                    # Salary / Expense deltas for risk and cash flow
                    sal_scale = float(overrides.get("monthly_salary_scale", 1.0))
                    sal_delta = float(overrides.get("monthly_salary_delta", 0.0))
                    exp_scale = float(overrides.get("monthly_expense_scale", 1.0))
                    exp_delta = float(overrides.get("monthly_expense_delta", 0.0))

                    adj_salary = max(0.0, (monthly_salary * sal_scale) + sal_delta)
                    adj_income = max(0.0, (total_monthly_income - monthly_salary) + adj_salary)
                    adj_expenses = max(0.0, (avg_monthly_expenses * exp_scale) + exp_delta)

                    # Net lump sum monthly impact over 12m projection
                    total_lump_out = sum(_to_float(item.get("amount")) for item in overrides.get("lump_sum_outflows", []))
                    total_lump_in = sum(_to_float(item.get("amount")) for item in overrides.get("lump_sum_inflows", []))
                    lump_monthly_net = (total_lump_out - total_lump_in) / 12.0

                    sc_risk_svc = RiskAnalysisService(
                        today=self.today,
                        net_worth_service=self._net_worth_service,
                        salary_override=adj_salary if adj_salary != monthly_salary else None,
                        monthly_expenses_override=adj_expenses if adj_expenses != avg_monthly_expenses else None,
                    )
                    sc_risk_score = _to_float(sc_risk_svc.payload().get("risk_score", {}).get("score"))

                    sc_coverage = round(cash_balance / adj_expenses, 1) if adj_expenses > 0 else None
                    sc_total_debt = real_debt_baseline + added_debt

                    # Retirement readiness presentation metric
                    target_age_to_use = sc_target_age if sc_target_age is not None else self.config["DEFAULT_RETIREMENT_AGE"]
                    sc_retire = self._compute_retirement_readiness(
                        sc_nw_12m, adj_expenses, target_age_to_use
                    )

                    # Per-scenario capacity-sensitive goal achievement (% of goals with sufficient monthly capacity)
                    sc_monthly_capacity = max(0.0, (adj_income - adj_expenses) - lump_monthly_net)
                    sc_goal_svc = GoalPlanningService(
                        today=self.today,
                        net_worth_service=self._net_worth_service,
                        monthly_capacity_override=sc_monthly_capacity,
                    )
                    sc_goal_payload = sc_goal_svc.payload()
                    sc_goals_list = sc_goal_payload.get("goals", [])
                    if sc_goals_list:
                        unfavorable_statuses = {"at_risk", "critical"}
                        favorable_count = sum(1 for g in sc_goals_list if g.get("status") not in unfavorable_statuses)
                        sc_goal_pct = round((favorable_count / len(sc_goals_list)) * 100.0, 1)
                    else:
                        sc_goal_pct = 100.0

                    sc_dict = {
                        "id": sc.id,
                        "name": sc.name,
                        "description": sc.description,
                        "is_baseline_pinned": sc.is_baseline_pinned,
                        "net_worth_12m": round(sc_nw_12m, 2),
                        "monthly_salary": round(adj_salary, 2),
                        "monthly_income": round(adj_income, 2),
                        "monthly_expenses": round(adj_expenses, 2),
                        "monthly_cash_flow": round(adj_income - adj_expenses, 2),
                        "total_debt": round(sc_total_debt, 2),
                        "cash_coverage_months": sc_coverage,
                        "risk_score": round(sc_risk_score, 1),
                        "goal_achievement_pct": round(sc_goal_pct, 1),
                        "gold_allocation_pct": round(gold_pct, 1),
                        "retirement_readiness": sc_retire,
                        "series": [
                            {"month_end": pt["month_end"], "net_worth": pt["net_worth"]}
                            for pt in sc_pts
                        ],
                        "events": [ev.to_dict() for ev in events],
                    }
                    sc_dict["insights"] = self.generate_insights(baseline_dict, sc_dict)
                    scenarios_out.append(sc_dict)

            month_labels = ["Current"] + [pt["month_end"] for pt in baseline_pts[1:]]

            user_birth_year = None
            if self.user and hasattr(self.user, "profile") and self.user.profile and self.user.profile.birthday:
                user_birth_year = self.user.profile.birthday.year

            return {
                "as_of": self.today.isoformat(),
                "config": self.config,
                "user_birth_year": user_birth_year,
                "recommended_bands": {
                    key: {"min_pct": band.min_pct, "max_pct": band.max_pct}
                    for key, band in PortfolioOptimizerService.RECOMMENDED_BANDS.items()
                },
                "baseline": baseline_dict,
                "scenarios": scenarios_out,
                "month_labels": month_labels,
            }

        except Exception as exc:  # noqa: BLE001
            # Defensive: always return valid JSON payload
            return {
                "as_of": self.today.isoformat(),
                "error": str(exc),
                "config": self.config,
                "recommended_bands": {},
                "baseline": {
                    "id": 0,
                    "name": "Baseline",
                    "description": "Baseline fallback",
                    "net_worth_12m": 0.0,
                    "monthly_cash_flow": 0.0,
                    "total_debt": 0.0,
                    "cash_coverage_months": None,
                    "risk_score": 0.0,
                    "goal_achievement_pct": 0.0,
                    "gold_allocation_pct": 0.0,
                    "retirement_readiness": {},
                    "series": [],
                },
                "scenarios": [],
                "month_labels": [],
            }
