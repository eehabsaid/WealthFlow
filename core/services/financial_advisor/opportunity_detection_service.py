from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from core.services.balance.net_worth_service import NetWorthService
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService


class OpportunityDetectionService:
    def __init__(self, today: date | None = None):
        self.today = today or date.today()
        self._net_worth_service = NetWorthService()
        self._optimizer_service = PortfolioOptimizerService(today=self.today)

    def payload(self) -> Dict[str, Any]:
        optimizer_payload = self._optimizer_service.payload()
        base_opportunities = optimizer_payload.get("opportunities", [])

        if not base_opportunities:
            return {
                "as_of": self.today.isoformat(),
                "opportunities": [],
                "count": 0,
            }

        # Single authoritative source for all net worth & forecast signal data
        cert_forecast = self._net_worth_service.certificate_forecast_payload(today=self.today)

        cash_balance = float(cert_forecast.get("cash_balance", 0.0) or 0.0)
        avg_monthly_expenses = float(cert_forecast.get("avg_monthly_expenses", 0.0) or 0.0)
        raw_idle_cash = cash_balance - (avg_monthly_expenses * 6.0)
        idle_cash = max(0.0, raw_idle_cash)

        gold_trend_7 = float(cert_forecast.get("gold_trend_7", 0.0) or 0.0)
        gold_trend_30 = float(cert_forecast.get("gold_trend_30", 0.0) or 0.0)

        total_net_worth = float(cert_forecast.get("net_worth", 0.0) or 0.0)
        current_gold_value_egp = float(cert_forecast.get("gold_value", 0.0) or 0.0)

        alloc_pcts = cert_forecast.get("allocation_percentages", {})
        current_gold_pct = float(alloc_pcts.get("type_gold", 0.0) or 0.0)

        # Dynamic target band threshold directly from PortfolioOptimizerService constant
        gold_band = PortfolioOptimizerService.RECOMMENDED_BANDS.get("gold")
        target_gold_min_pct = gold_band.min_pct if gold_band else 10.0

        target_gold_value_egp = (target_gold_min_pct / 100.0) * total_net_worth
        gold_shortfall_egp = max(0.0, target_gold_value_egp - current_gold_value_egp)

        upcoming_certs = cert_forecast.get("upcoming", [])
        nearest_cert = upcoming_certs[0] if upcoming_certs else None

        enriched_opportunities: List[Dict[str, Any]] = []
        for opp in base_opportunities:
            key = str(opp.get("key", ""))
            severity = opp.get("severity", "medium")
            severity_key = opp.get("severity_key", f"portfolio_optimizer_severity_{severity}")
            impact_key = opp.get("impact_key", "")

            if "gold" in key:
                signals = {
                    "idle_cash": round(idle_cash, 2),
                    "gold_trend_7d": round(gold_trend_7, 2),
                    "gold_trend_30d": round(gold_trend_30, 2),
                    "current_gold_allocation_pct": round(current_gold_pct, 1),
                    "target_gold_min_pct": round(target_gold_min_pct, 1),
                    "shortfall_egp": round(gold_shortfall_egp, 2),
                }
                enriched_opportunities.append({
                    "key": key,
                    "title_key": key,
                    "severity": severity,
                    "severity_key": severity_key,
                    "impact_key": impact_key,
                    "signals": signals,
                    "highlighted_amount": round(gold_shortfall_egp, 2),
                    "action_template_key": "opp_gold_action",
                    "action_params": {
                        "amount": round(gold_shortfall_egp, 2),
                        "target_pct": round(target_gold_min_pct, 1),
                    },
                })
            elif "maturity" in key or "maturities" in key:
                if nearest_cert:
                    mat_val = float(nearest_cert.get("maturity_value", 0.0) or 0.0)
                    days_left = int(nearest_cert.get("days_left", 0) or 0)
                    signals = {
                        "maturity_date": nearest_cert.get("expiry_date", ""),
                        "days_left": days_left,
                        "maturity_value": round(mat_val, 2),
                        "amount": round(float(nearest_cert.get("amount", 0.0) or 0.0), 2),
                        "interest": round(float(nearest_cert.get("interest", 0.0) or 0.0), 2),
                        "bank": nearest_cert.get("bank", ""),
                    }
                    enriched_opportunities.append({
                        "key": key,
                        "title_key": "opp_maturity_title",
                        "severity": severity,
                        "severity_key": severity_key,
                        "impact_key": impact_key,
                        "signals": signals,
                        "highlighted_amount": round(mat_val, 2),
                        "action_template_key": "opp_maturity_action",
                        "action_params": {
                            "amount": round(mat_val, 2),
                            "days": days_left,
                        },
                    })
                else:
                    enriched_opportunities.append({
                        "key": key,
                        "title_key": key,
                        "severity": severity,
                        "severity_key": severity_key,
                        "impact_key": impact_key,
                    })
            else:
                enriched_opportunities.append({
                    "key": key,
                    "title_key": key,
                    "severity": severity,
                    "severity_key": severity_key,
                    "impact_key": impact_key,
                })

        return {
            "as_of": self.today.isoformat(),
            "opportunities": enriched_opportunities,
            "count": len(enriched_opportunities),
        }
