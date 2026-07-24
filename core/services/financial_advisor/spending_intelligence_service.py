from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Sum, Count
from django.db.models.functions import Coalesce

from core.models import Expense
from core.services.balance.net_worth_service import NetWorthService


class SpendingIntelligenceService:
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
        categories = []
        most_frequent = None
        max_count = -1

        # Use aggregation to avoid fetching all expenses into memory
        cat_qs = Expense.objects.values('category__name', 'category__icon').annotate(
            amount=Coalesce(Sum('amount_egp'), Decimal('0.0')),
            count=Count('id')
        ).order_by('-amount')

        for item in cat_qs:
            name = item['category__name'] or "spending_intelligence_uncategorized"
            icon = item['category__icon'] or "💰"
            amount = self._to_float(item['amount'])
            count = int(item['count'])

            pct = (amount / total_expenses * 100.0) if total_expenses > 0 else 0.0

            categories.append({
                "name": name,
                "icon": icon,
                "amount_egp": round(amount, 2),
                "count": count,
                "percentage": round(pct, 1)
            })

            # Track most frequent category
            if count > max_count:
                max_count = count
                
                # Fetch months_span specifically for the most frequent category
                if item['category__name']:
                    months_qs = Expense.objects.filter(category__name=item['category__name']).values('year', 'month').distinct()
                else:
                    months_qs = Expense.objects.filter(category__isnull=True).values('year', 'month').distinct()
                months_span = months_qs.count()
                avg_per_tx = amount / count if count > 0 else 0.0
                
                most_frequent = {
                    "name": name,
                    "count": count,
                    "months_span": months_span,
                    "avg_per_tx": round(avg_per_tx, 2)
                }

        # 4. Largest single expense
        largest_expense_obj = Expense.objects.select_related('category').order_by('-amount_egp', '-id').first()
        largest_expense = None
        if largest_expense_obj:
            cat_name = largest_expense_obj.category.name if largest_expense_obj.category else "spending_intelligence_uncategorized"
            desc = largest_expense_obj.description.strip() if largest_expense_obj.description else (largest_expense_obj.notes.strip() if largest_expense_obj.notes else "")
            largest_expense = {
                "amount_egp": self._to_float(largest_expense_obj.amount_egp),
                "category": cat_name,
                "description": desc,
                "date": largest_expense_obj.date.isoformat() if largest_expense_obj.date else ""
            }

        # 5. Monthly comparison
        months = []
        monthly_qs = Expense.objects.values('year', 'month').annotate(
            total_egp=Coalesce(Sum('amount_egp'), Decimal('0.0')),
            count=Count('id')
        ).order_by('year', 'month')

        for item in monthly_qs:
            months.append({
                "year": item['year'],
                "month": item['month'],
                "total_egp": round(self._to_float(item['total_egp']), 2),
                "count": int(item['count'])
            })

        insufficient_history = len(months) < 3

        # 6. AI Insights & Recommendations
        insights = []
        recommendations = []

        if len(months) >= 2:
            last_month = months[-1]
            prev_month = months[-2]
            if prev_month["total_egp"] > 0:
                diff_pct = ((last_month["total_egp"] - prev_month["total_egp"]) / prev_month["total_egp"]) * 100.0
                
                if diff_pct > 15:
                    insights.append({
                        "key": "spending_intelligence_insight_increased",
                        "params": {"pct": str(round(diff_pct, 1))}
                    })
                elif diff_pct < -15:
                    insights.append({
                        "key": "spending_intelligence_insight_decreased",
                        "params": {"pct": str(round(abs(diff_pct), 1))}
                    })

        if len(categories) > 0:
            top_cat = categories[0]
            if top_cat["percentage"] > 40:
                insights.append({
                    "key": "spending_intelligence_insight_dominates",
                    "params": {"category": top_cat["name"], "pct": str(round(top_cat["percentage"], 1))}
                })
            
            # Data-driven recommendations
            recommendations.append({
                "key": "spending_intelligence_rec_food_pct",
                "params": {"pct": str(round(top_cat["percentage"], 1)), "category": top_cat["name"]},
                "priority": "High" if top_cat["percentage"] > 30 else "Medium"
            })
            
            if len(categories) > 1:
                 second_cat = categories[1]
                 recommendations.append({
                     "key": "spending_intelligence_rec_family_largest",
                     "params": {"category": second_cat["name"]},
                     "priority": "Medium"
                 })

        if len(months) >= 2:
             last_month = months[-1]
             prev_month = months[-2]
             if prev_month["total_egp"] > 0 and last_month["total_egp"] > prev_month["total_egp"]:
                 diff_pct = ((last_month["total_egp"] - prev_month["total_egp"]) / prev_month["total_egp"]) * 100.0
                 recommendations.append({
                     "key": "spending_intelligence_rec_transport_increased",
                     "params": {"pct": str(round(diff_pct, 1))},
                     "priority": "High" if diff_pct > 15 else "Medium"
                 })

        if len(categories) >= 3 and categories[0]["percentage"] < 30:
             recommendations.append({
                 "key": "spending_intelligence_rec_balanced",
                 "params": {},
                 "priority": "Low"
             })
        elif len(recommendations) < 3:
             # Add fallback recommendation
             recommendations.append({
                 "key": "spending_intelligence_rec_discretionary",
                 "params": {},
                 "priority": "Low"
             })
             
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
            "key_findings": {
                "most_frequent": most_frequent,
                "largest_expense": largest_expense
            },
            "monthly_comparison": {
                "months": months,
                "insufficient_history": insufficient_history
            },
            "ai_insights": insights,
            "recommended_actions": recommendations
        }
