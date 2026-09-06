from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce

from core.models import Expense
from core.services.balance.net_worth_service import NetWorthService

from .categories import CategoriesMixin
from .insights import InsightsMixin
from .monthly import MonthlyComparisonMixin


class SpendingIntelligenceService(CategoriesMixin, MonthlyComparisonMixin, InsightsMixin):
    def __init__(self, today: date | None = None, net_worth_service: NetWorthService | None = None):
        self.today = today or date.today()
        self.net_worth_service = net_worth_service or NetWorthService()

    def _to_float(self, value) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def payload(self) -> dict:
        # 1. Fetch avg_monthly_expenses from NetWorthService to avoid recalculating
        nw_payload = self.net_worth_service.certificate_forecast_payload(today=self.today)
        avg_monthly_expenses = self._to_float(nw_payload.get("avg_monthly_expenses", 0.0))

        # 2. Get total expenses for the dataset to calculate percentages
        total_expenses_agg = Expense.objects.aggregate(total=Coalesce(Sum('amount_egp'), Decimal('0.0')))
        total_expenses = self._to_float(total_expenses_agg['total'])

        # 3. Aggregate categories
        categories, most_frequent = self._build_categories(total_expenses)

        # 4. Largest single expense
        largest_expense = self._largest_expense()

        # 5. Registered Categories for filtering
        registered_categories = self._registered_categories()
        has_uncategorized = Expense.objects.filter(category__isnull=True).exists()

        # 6. Monthly comparison (overall and by category)
        months, by_category = self._monthly_comparison()
        insufficient_history = len(months) < 3

        # 7. AI Insights & Recommendations
        insights = self._build_insights(months, categories)
        recommendations = self._build_recommendations(months, categories)

        total_transactions = Expense.objects.count()
        avg_transactions_per_month = total_transactions / len(months) if len(months) > 0 else 0

        return {
            "as_of": self.today.isoformat(),
            "avg_monthly_expenses": round(avg_monthly_expenses, 2),
            "total_expenses_recorded": round(self._to_float(Expense.objects.aggregate(t=Coalesce(Sum('amount_egp'), Decimal('0.0')))['t']), 2),
            "total_transactions": total_transactions,
            "avg_transactions_per_month": round(avg_transactions_per_month, 1),
            "months_history": len(months),
            "categories": categories,
            "registered_categories": registered_categories,
            "has_uncategorized": has_uncategorized,
            "key_findings": {
                "most_frequent": most_frequent,
                "largest_expense": largest_expense
            },
            "monthly_comparison": {
                "months": months,
                "by_category": by_category,
                "insufficient_history": insufficient_history
            },
            "ai_insights": insights,
            "recommended_actions": recommendations
        }
