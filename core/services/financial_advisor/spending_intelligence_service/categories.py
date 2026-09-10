from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from core.models import Expense, ExpenseCategory


class CategoriesMixin:
    """Per-category aggregation, most-frequent category, largest expense,
    and the registered-categories list used for filtering."""

    def _build_categories(self, total_expenses: float):
        categories = []
        most_frequent = None
        max_count = -1

        cat_qs = Expense.objects.filter(owner=self.owner).values('category__name', 'category__icon').annotate(
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
                    months_qs = Expense.objects.filter(owner=self.owner, category__name=item['category__name']).values('year', 'month').distinct()
                else:
                    months_qs = Expense.objects.filter(owner=self.owner, category__isnull=True).values('year', 'month').distinct()
                months_span = months_qs.count()
                avg_per_tx = amount / count if count > 0 else 0.0

                most_frequent = {
                    "name": name,
                    "count": count,
                    "months_span": months_span,
                    "avg_per_tx": round(avg_per_tx, 2)
                }

        return categories, most_frequent

    def _largest_expense(self):
        largest_expense_obj = Expense.objects.filter(owner=self.owner).select_related('category').order_by('-amount_egp', '-id').first()
        if not largest_expense_obj:
            return None

        cat_name = largest_expense_obj.category.name if largest_expense_obj.category else "spending_intelligence_uncategorized"
        desc = largest_expense_obj.description.strip() if largest_expense_obj.description else (largest_expense_obj.notes.strip() if largest_expense_obj.notes else "")
        return {
            "amount_egp": self._to_float(largest_expense_obj.amount_egp),
            "category": cat_name,
            "description": desc,
            "date": largest_expense_obj.date.isoformat() if largest_expense_obj.date else ""
        }

    def _registered_categories(self):
        return [
            {
                "id": cat.id,
                "name": cat.name,
                "icon": cat.icon,
                "color_hex": cat.color_hex
            }
            for cat in ExpenseCategory.objects.filter(owner=self.owner).order_by('order', 'name')
        ]
