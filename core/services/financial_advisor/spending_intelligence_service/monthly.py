from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from core.models import Expense


class MonthlyComparisonMixin:
    """Monthly totals overall and broken down by category."""

    def _monthly_comparison(self):
        months = []
        monthly_qs = Expense.objects.filter(owner=self.owner).values('year', 'month').annotate(
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

        by_category = {}
        monthly_cat_qs = Expense.objects.filter(owner=self.owner).values('year', 'month', 'category_id').annotate(
            total_egp=Coalesce(Sum('amount_egp'), Decimal('0.0')),
            count=Count('id')
        ).order_by('year', 'month')

        for item in monthly_cat_qs:
            cat_key = str(item['category_id']) if item['category_id'] is not None else "uncategorized"
            if cat_key not in by_category:
                by_category[cat_key] = []
            by_category[cat_key].append({
                "year": item['year'],
                "month": item['month'],
                "total_egp": round(self._to_float(item['total_egp']), 2),
                "count": int(item['count'])
            })

        return months, by_category
