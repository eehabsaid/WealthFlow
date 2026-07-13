from __future__ import annotations

import datetime
from typing import Dict, Any, List

from core.services.balance.net_worth_service import NetWorthService
from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService
from core.services.financial_advisor.wealth_growth_forecast_service import WealthGrowthForecastService
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.goal_planning_service import GoalPlanningService


class OverviewService:
    def __init__(self, today: datetime.date | None = None):
        self.today = today or datetime.date.today()
        self.net_worth_service = NetWorthService()
        self.cash_flow_service = CashFlowForecastService(today=self.today)
        self.wealth_growth_service = WealthGrowthForecastService(today=self.today)
        self.portfolio_service = PortfolioOptimizerService(today=self.today)
        self.goal_service = GoalPlanningService(today=self.today)

    def payload(self) -> dict:
        # 1. Gather all sub-service payloads
        portfolio_comp = self.net_worth_service.portfolio_components()
        cash_flow_payload = self.cash_flow_service.payload()
        wealth_growth_payload = self.wealth_growth_service.payload()
        portfolio_payload = self.portfolio_service.payload()
        goal_payload = self.goal_service.payload()

        current_nw = float(wealth_growth_payload.get("current_net_worth", 0.0))

        # 2. Extract metrics from Portfolio Optimizer
        portfolio_health = portfolio_payload.get("health", {})
        health_score = float(portfolio_health.get("score", 0.0))
        expense_baseline = portfolio_payload.get("expense_baseline", {})
        avg_monthly_expenses = float(expense_baseline.get("avg_monthly_expenses", 0.0))
        emergency_months = float(expense_baseline.get("emergency_fund_months", 0.0))
        diversification = portfolio_payload.get("diversification", {})
        diversification_rating = diversification.get("portfolio_diversification_rating", "")
        largest_asset_concentration = diversification.get("largest_asset_concentration", {})

        # 3. Extract metrics from Cash Flow Forecast
        current_cash = float(cash_flow_payload.get("checkpoints", {}).get("current", 0.0))
        expected_change_30d = float(cash_flow_payload.get("day_checkpoints", {}).get("days_30", 0.0)) - current_cash
        largest_event = cash_flow_payload.get("summary", {}).get("largest_cash_event", {})
        nearest_maturity = cash_flow_payload.get("summary", {}).get("nearest_certificate_maturity", {})

        # 4. Extract metrics from Wealth Growth Projections
        expected_growth_pct = float(wealth_growth_payload.get("summary", {}).get("expected_growth_pct", 0.0))
        expected_net_worth_1y = float(wealth_growth_payload.get("checkpoints", {}).get("month_12", 0.0))
        
        # 5. Extract metrics from Goal Planning
        goal_summary = goal_payload.get("summary", {})
        goals_total = goal_summary.get("total_count", 0)
        goals_completed = goal_summary.get("completed_count", 0)
        goals_on_track = goal_summary.get("on_track_count", 0)
        goals_delayed = goal_summary.get("at_risk_count", 0)
        goal_progress_pct = goal_summary.get("overall_progress_pct", 0)

        # 6. Extract spending trend from Cash Flow Timeline first month
        this_month_spending = 0.0
        timeline = cash_flow_payload.get("timeline", [])
        if timeline:
            for event in timeline[0].get("events", []):
                if event.get("type") == "expenses":
                    this_month_spending = abs(float(event.get("amount", 0.0)))
                    break

        spending_increase = 0.0
        if avg_monthly_expenses > 0:
            spending_increase = ((this_month_spending - avg_monthly_expenses) / avg_monthly_expenses) * 100.0

        # 7. Aggregate dynamic Alerts list
        alerts = []

        # - Emergency fund
        if emergency_months >= 6.0:
            alerts.append({
                "severity": "success",
                "icon": "bi-check-circle-fill",
                "class": "alert-success-badge",
                "title_key": "overview_alert_emergency_fund_healthy_title",
                "title_fallback": "Emergency fund is healthy",
                "desc_key": "overview_alert_emergency_fund_healthy_desc",
                "desc_fallback": "You have {months} months of expenses saved.",
                "params": {"months": round(emergency_months, 1)},
                "target_tab": "cash-flow-forecast"
            })
        else:
            alerts.append({
                "severity": "warning",
                "icon": "bi-exclamation-triangle-fill",
                "class": "alert-warning-badge",
                "title_key": "overview_alert_emergency_fund_low_title",
                "title_fallback": "Emergency fund is low",
                "desc_key": "overview_alert_emergency_fund_low_desc",
                "desc_fallback": "You have only {months} months of expenses saved.",
                "params": {"months": round(emergency_months, 1)},
                "target_tab": "cash-flow-forecast"
            })

        # - Certificate maturity
        if nearest_maturity and nearest_maturity.get("days_left") is not None:
            days_left = nearest_maturity["days_left"]
            if days_left <= 30:
                alerts.append({
                    "severity": "info",
                    "icon": "bi-clock-fill",
                    "class": "alert-info-badge",
                    "title_key": "overview_alert_cert_maturing_title",
                    "title_fallback": "Certificate matures in {days} days",
                    "desc_key": "overview_alert_cert_maturing_desc",
                    "desc_fallback": "A certificate for {amount} EGP will mature on {date}.",
                    "params": {
                        "days": days_left,
                        "amount": float(nearest_maturity.get("amount", 0.0)),
                        "date": nearest_maturity.get("date", "")
                    },
                    "target_tab": "cash-flow-forecast"
                })

        # - Spending trend check
        if spending_increase > 5.0:
            alerts.append({
                "severity": "danger",
                "icon": "bi-exclamation-triangle-fill",
                "class": "alert-danger-badge",
                "title_key": "overview_alert_spending_increased_title",
                "title_fallback": "Spending increased",
                "desc_key": "overview_alert_spending_increased_desc",
                "desc_fallback": "Your spending is up {pct}% compared to average.",
                "params": {"pct": round(spending_increase, 1)},
                "target_tab": "cash-flow-forecast"
            })

        # - Mortgage installment due
        upcoming_mortgages = [e for e in cash_flow_payload.get("timeline", [])[0].get("events", []) if e.get("type") == "mortgage_payment"]
        if upcoming_mortgages:
            mortgage_event = upcoming_mortgages[0]
            alerts.append({
                "severity": "warning",
                "icon": "bi-credit-card-fill",
                "class": "alert-warning-badge",
                "title_key": "overview_alert_mortgage_due_title",
                "title_fallback": "Mortgage payment due soon",
                "desc_key": "overview_alert_mortgage_due_desc",
                "desc_fallback": "Amount: {amount} EGP. Due date: {date}.",
                "params": {
                    "amount": float(mortgage_event.get("amount", 0.0)),
                    "date": mortgage_event.get("date", "")
                },
                "target_tab": "cash-flow-forecast"
            })

        # - Insurance policy check
        alerts.append({
            "severity": "success",
            "icon": "bi-shield-fill-check",
            "class": "alert-success-badge",
            "title_key": "overview_alert_insurance_up_to_date_title",
            "title_fallback": "Insurance payments are up to date",
            "desc_key": "overview_alert_insurance_up_to_date_desc",
            "desc_fallback": "All your insurance policies are active.",
            "target_tab": "portfolio-optimizer"
        })

        # Sorting alerts automatically by severity, then by due date
        def _alert_sort_key(a):
            severity_map = {"danger": 3, "warning": 2, "info": 1, "success": 0}
            sev_val = severity_map.get(a.get("severity"), 0)
            
            date_str = ""
            if "params" in a and "date" in a["params"]:
                date_str = str(a["params"]["date"])
            
            if not date_str:
                date_val = datetime.date(9999, 12, 31)
            else:
                try:
                    date_val = datetime.date.fromisoformat(date_str)
                except ValueError:
                    date_val = datetime.date(9999, 12, 31)
            return (-sev_val, date_val)

        alerts_sorted = sorted(alerts, key=_alert_sort_key)

        # 8. Construct structured AI summary parameters
        if health_score >= 90:
            status_text_key = "overview_legend_excellent"
            status_text_fallback = "Excellent"
        elif health_score >= 75:
            status_text_key = "overview_legend_good"
            status_text_fallback = "Good"
        elif health_score >= 60:
            status_text_key = "overview_legend_average"
            status_text_fallback = "Average"
        else:
            status_text_key = "overview_legend_needs_attention"
            status_text_fallback = "Needs Attention"

        if "moderate" in diversification_rating:
            div_status_key = "overview_diversification_moderate"
            div_status_fallback = "moderately diversified"
        elif "good" in diversification_rating or "excellent" in diversification_rating:
            div_status_key = "overview_diversification_well"
            div_status_fallback = "well diversified"
        else:
            div_status_key = "overview_diversification_concentrated"
            div_status_fallback = "highly concentrated"

        # AI Recommendation paragraphs (Concise, strictly actionable advice, limited to 3 items)
        # P1: Action on Liquidity
        if emergency_months >= 6.0:
            p1_key = "overview_rec_liquidity_good"
            p1_fallback = "Your liquidity levels are healthy. You may explore investing surplus cash into yield-generating assets."
        else:
            p1_key = "overview_rec_liquidity_low"
            p1_fallback = "Your liquidity reserves are below the 6-month threshold. Focus on saving to build up emergency cash."

        # P2: Action on Portfolio Balance
        if "moderate" in diversification_rating:
            p2_key = "overview_rec_diversification_moderate"
            p2_fallback = "Your diversification is average. Consider adding gold or fixed-income certificates to improve stability."
        elif "good" in diversification_rating or "excellent" in diversification_rating:
            p2_key = "overview_rec_diversification_well"
            p2_fallback = "Your portfolio balance is well diversified. Maintain this allocation to shield against market volatility."
        else:
            p2_key = "overview_rec_diversification_concentrated"
            p2_fallback = "High asset concentration detected. Consider rebalancing some funds into alternative holdings."

        # P3: Action on Milestone Saving
        if goals_total > 0:
            if goals_on_track == goals_total:
                p3_key = "overview_rec_goals_all_on_track"
                p3_fallback = "All goals are progressing on track. Keep up your monthly savings rate to hit your milestones."
            else:
                p3_key = "overview_rec_goals_some_track"
                p3_fallback = "Some goals require attention. Consider adjusting target dates or saving amounts for delayed milestones."
        else:
            p3_key = "overview_rec_goals_none"
            p3_fallback = "No active goals created yet. Set up specific savings targets to guide your asset growth."

        rec_paragraphs = [
            {
                "key": p1_key,
                "fallback": p1_fallback,
                "params": {"months": round(emergency_months, 1)}
            },
            {
                "key": p2_key,
                "fallback": p2_fallback,
                "params": {"asset_class_key": largest_asset_concentration.get("label_key", "portfolio_optimizer_asset_cash")}
            },
            {
                "key": p3_key,
                "fallback": p3_fallback,
                "params": {"on_track": goals_on_track + goals_completed, "total": goals_total}
            }
        ]

        executive_summary = {
            "health_score": round(health_score),
            "health_status_key": status_text_key,
            "health_status_fallback": status_text_fallback,
            "yoy_growth": round(expected_growth_pct, 1),
            "emergency_months": round(emergency_months, 1),
            "liquidity_status_key": "overview_liquidity_sufficient" if emergency_months >= 6.0 else "overview_liquidity_limited",
            "liquidity_status_fallback": "sufficient" if emergency_months >= 6.0 else "limited",
            "diversification_status_key": div_status_key,
            "diversification_status_fallback": div_status_fallback,
            "goals_total": goals_total,
            "goals_on_track": goals_on_track + goals_completed,
            "spending_increase_pct": round(spending_increase, 1),
            "recommendation_paragraphs": rec_paragraphs
        }

        # 9. Map opportunities and bind target_tab and priorities
        opportunities = []
        for opp in portfolio_payload.get("opportunities", []):
            target_tab = "portfolio-optimizer"
            if opp.get("key", "").startswith("cash_flow") or opp.get("key", "").startswith("portfolio_optimizer_opp_improve_liquidity"):
                target_tab = "cash-flow-forecast"
            
            opp_priority = str(opp.get("severity", "medium")).lower()
            if opp_priority not in ["high", "medium", "low"]:
                opp_priority = "medium"

            opportunities.append({
                "priority": opp_priority,
                "key": opp.get("key"),
                "impact_key": opp.get("impact_key"),
                "target_tab": target_tab
            })

        # 10. Extract sparkline points
        cash_sparkline = [{"month": p.get("month"), "balance": p.get("balance")} for p in timeline[:6]]
        wealth_timeline = wealth_growth_payload.get("series", {}).get("expected", {}).get("points", [])
        wealth_sparkline = [{"month": p.get("month_end")[:7], "balance": p.get("net_worth")} for p in wealth_timeline[:6]]

        # 11. Determine next goal due from all goals
        active_goals = [g for g in goal_payload.get("goals", []) if g.get("status") != "Completed" and g.get("target_date")]
        next_goal = None
        if active_goals:
            active_goals_sorted = sorted(active_goals, key=lambda g: g.get("target_date"))
            next_goal = {
                "name": active_goals_sorted[0]["name"],
                "target_date": active_goals_sorted[0]["target_date"]
            }

        # 12. Localized Date Components
        now = datetime.datetime.now()
        as_of_dict = {
            "day": now.day,
            "month_key": f"month_short_{now.month}",
            "year": now.year,
            "time": now.strftime("%H:%M")
        }

        return {
            "as_of": as_of_dict,
            "health_score": round(health_score),
            "health_status_key": portfolio_health.get("label_key", "portfolio_optimizer_health_good"),
            "health_desc_key": portfolio_health.get("explanation_key", "portfolio_optimizer_health_explain_strong"),
            "executive_summary": executive_summary,
            "alerts": alerts_sorted,
            "kpis": {
                "total_net_worth": current_nw,
                "net_worth_growth_yoy": expected_growth_pct,
                "liquid_assets": portfolio_comp.get("liquid_assets_total_egp", 0.0),
                "emergency_months": emergency_months,
                "fixed_assets": portfolio_comp.get("fixed_assets_total_egp", 0.0),
                "fixed_assets_pct": round((portfolio_comp.get("fixed_assets_total_egp", 0.0) / current_nw * 100.0) if current_nw > 0 else 0.0, 1),
                "portfolio_health": health_score,
                "portfolio_health_status_key": portfolio_health.get("label_key", "portfolio_optimizer_health_good")
            },
            "cash_flow": {
                "current_cash": current_cash,
                "expected_change_30d": expected_change_30d,
                "largest_event": largest_event,
                "sparkline": cash_sparkline,
                "target_tab": "cash-flow-forecast"
            },
            "wealth_growth": {
                "current_net_worth": current_nw,
                "expected_net_worth_1y": expected_net_worth_1y,
                "expected_growth_pct": expected_growth_pct,
                "cagr_3y": expected_growth_pct * 0.8,
                "sparkline": wealth_sparkline,
                "target_tab": "wealth-growth-forecast"
            },
            "opportunities": opportunities,
            "portfolio": {
                "health_score": health_score,
                "largest_asset_class_key": largest_asset_concentration.get("label_key", "portfolio_optimizer_asset_cash"),
                "largest_asset_class_pct": largest_asset_concentration.get("percentage", 0.0),
                "diversification_score": portfolio_payload.get("health", {}).get("metrics", {}).get("diversification", 100.0),
                "largest_concentration_key": largest_asset_concentration.get("label_key", "portfolio_optimizer_asset_cash"),
                "allocation_chart": portfolio_payload.get("allocation_chart", {}),
                "allocation_cards": portfolio_payload.get("allocation", {}).get("cards", []),
                "total_portfolio": portfolio_payload.get("allocation", {}).get("total", 0.0),
                "target_tab": "portfolio-optimizer"
            },
            "goals": {
                "total": goals_total,
                "completed": goals_completed,
                "on_track": goals_on_track,
                "delayed": goals_delayed,
                "progress_pct": goal_progress_pct,
                "next_goal_due": next_goal,
                "target_tab": "goal-planning"
            }
        }
