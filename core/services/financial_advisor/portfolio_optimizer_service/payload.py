"""Phase 2 of payload(): recommendations, opportunities, chart data, and
final dict assembly. Thin orchestrator on top of PortfolioContext built by
payload_metrics.py.

NOTE (200-line file convention): part of the split of
core/services/financial_advisor/portfolio_optimizer_service.py (659 lines).
"""
from __future__ import annotations

from .shared import _to_float


class PayloadMixin:
    def payload(self) -> dict:
        ctx = self._build_portfolio_context()

        recommendations = self._recommendations(ctx.allocation_percentages, ctx.emergency_months)
        maturity_egp_90 = self._upcoming_certificate_maturity_egp(ctx.comp, days=90)
        if maturity_egp_90 > 0:
            recommendations.append(
                {
                    "key": "portfolio_optimizer_rec_upcoming_maturities_boost_liquidity",
                    "severity": "info",
                    "severity_key": "portfolio_optimizer_severity_info",
                    "metric_value": round(maturity_egp_90, 2),
                }
            )
        priority_rank = {"high": 0, "medium": 1, "low": 2, "info": 3}
        recommendations.sort(key=lambda item: priority_rank.get(str(item.get("severity")), 99))
        opportunities = self._opportunities(ctx.allocation_percentages, recommendations, ctx.comp)

        chart_labels = [
            self.ALLOCATION_LABELS["cash"],
            self.ALLOCATION_LABELS["certificates"],
            self.ALLOCATION_LABELS["gold"],
            self.ALLOCATION_LABELS["real_estate"],
            self.ALLOCATION_LABELS["vehicles"],
            self.ALLOCATION_LABELS["other_assets"],
        ]
        chart_values = [
            ctx.allocation_values["cash"],
            ctx.allocation_values["certificates"],
            ctx.allocation_values["gold"],
            ctx.allocation_values["real_estate"],
            ctx.allocation_values["vehicles"],
            ctx.allocation_values["other_assets"],
        ]

        return {
            "as_of": self.today.isoformat(),
            "health": {
                "score": ctx.health_score,
                "label_key": self._health_label_key(ctx.health_score),
                "explanation_key": self._health_explanation_key(
                    score=ctx.health_score,
                    emergency_months=ctx.emergency_months,
                    largest_concentration_pct=ctx.largest_category_pct,
                    asset_classes_owned=ctx.categories_owned,
                    gold_pct=_to_float(ctx.allocation_percentages.get("gold")),
                ),
                "metrics": ctx.metrics,
            },
            "allocation": {
                "total": round(ctx.total_portfolio, 2),
                "cards": ctx.allocation_cards,
                "percentages": ctx.allocation_percentages,
            },
            "diversification": {
                "asset_classes_owned": ctx.categories_owned,
                "bank_accounts_used": len(ctx.bank_exposure),
                "largest_asset_concentration": {
                    "label_key": ctx.largest_category_label,
                    "percentage": round(ctx.largest_category_pct, 2),
                },
                "largest_bank_concentration": ctx.largest_bank,
                "largest_asset_type": ctx.largest_category_label,
                "largest_portfolio_allocation": {
                    "label_key": ctx.largest_category_label,
                    "percentage": round(ctx.largest_category_pct, 2),
                },
                "largest_currency_exposure": ctx.largest_currency,
                "portfolio_diversification_rating": ctx.diversification_rating_key,
            },
            "recommendations": recommendations,
            "asset_breakdown": ctx.top_assets,
            "allocation_chart": {
                "labels": chart_labels,
                "values": [round(value, 2) for value in chart_values],
            },
            "concentration": {
                "largest_asset": ctx.largest_asset,
                "largest_bank": ctx.largest_bank,
                "largest_balance": ctx.largest_balance,
                "largest_exposure": {
                    "label_key": ctx.largest_category_label,
                    "value": round(_to_float(ctx.allocation_values.get(ctx.largest_category_key)), 2),
                },
                "highest_appreciating_asset": ctx.highest_appreciating_asset,
                "largest_concentration_pct": round(ctx.largest_category_pct, 2),
                "warning": ctx.largest_category_pct > 50.0,
            },
            "opportunities": opportunities,
            "quality_checks": {
                "allocation_total_pct": round(sum(ctx.allocation_percentages.values()), 2),
                "recommendation_count": len(recommendations),
                "opportunity_count": len(opportunities),
            },
            "expense_baseline": {
                "avg_monthly_expenses": round(ctx.monthly_expenses, 2),
                "emergency_fund_months": round(ctx.emergency_months, 2),
            },
        }
