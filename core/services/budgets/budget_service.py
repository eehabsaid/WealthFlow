"""Budget CRUD + spend computation.

Spend is always computed from Expense.amount_base (already converted to
the owner's base currency at save time — see ExpenseService), so a
budget set in any currency compares correctly against expenses recorded
in any other currency. No hardcoded currency anywhere in this file.
"""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from core.models import Budget, Expense


class BudgetService:
    @staticmethod
    def period_range(period: str, ref_date: date):
        """Return (start, end) inclusive dates for the period containing ref_date."""
        if period == "weekly":
            start = ref_date - timedelta(days=ref_date.weekday())
            end = start + timedelta(days=6)
            return start, end
        if period == "yearly":
            return date(ref_date.year, 1, 1), date(ref_date.year, 12, 31)
        # monthly (default)
        last_day = monthrange(ref_date.year, ref_date.month)[1]
        return date(ref_date.year, ref_date.month, 1), date(ref_date.year, ref_date.month, last_day)

    @staticmethod
    def compute_spent(budget: Budget, ref_date: date = None) -> Decimal:
        ref_date = ref_date or date.today()
        start, end = BudgetService.period_range(budget.period, ref_date)
        qs = Expense.objects.filter(owner=budget.owner, date__gte=start, date__lte=end)
        if budget.category_id:
            qs = qs.filter(category_id=budget.category_id)
        total = qs.aggregate(total=Sum("amount_base"))["total"]
        return Decimal(total or 0)

    @staticmethod
    @transaction.atomic
    def create_budget(data, owner) -> Budget:
        from core.services.shared.base_currency import get_user_base_code
        from core.services.shared.currency_conversion_service import CurrencyConversionService

        amount_value = Decimal(str(data.get("amount", 0) or 0))
        currency_id = data.get("currency_id")
        exchange_rate = Decimal("1")
        if currency_id:
            from core.models import Currency

            curr = Currency.objects.filter(id=currency_id).first()
            if curr:
                exchange_rate = CurrencyConversionService.strict_rate(
                    curr.code, get_user_base_code(owner)
                )
        return Budget.objects.create(
            owner=owner,
            name=data["name"],
            category_id=data.get("category_id"),
            period=data.get("period", "monthly"),
            amount=amount_value,
            currency_id=currency_id,
            amount_base=amount_value * exchange_rate,
            alert_threshold_percent=int(data.get("alert_threshold_percent", 80)),
            is_active=data.get("is_active", True),
        )

    @staticmethod
    @transaction.atomic
    def update_budget(budget: Budget, data) -> Budget:
        from core.services.shared.base_currency import get_user_base_code
        from core.services.shared.currency_conversion_service import CurrencyConversionService

        if "name" in data:
            budget.name = data["name"]
        if "category_id" in data:
            budget.category_id = data["category_id"]
        if "period" in data:
            budget.period = data["period"]
        if "alert_threshold_percent" in data:
            budget.alert_threshold_percent = int(data["alert_threshold_percent"])
        if "is_active" in data:
            budget.is_active = data["is_active"]
        if "amount" in data or "currency_id" in data:
            amount_value = Decimal(str(data.get("amount", budget.amount) or 0))
            currency_id = data.get("currency_id", budget.currency_id)
            exchange_rate = Decimal("1")
            if currency_id:
                from core.models import Currency

                curr = Currency.objects.filter(id=currency_id).first()
                if curr:
                    exchange_rate = CurrencyConversionService.strict_rate(
                        curr.code, get_user_base_code(budget.owner)
                    )
            budget.amount = amount_value
            budget.currency_id = currency_id
            budget.amount_base = amount_value * exchange_rate
        budget.save()
        return budget

    @staticmethod
    def list_with_spend(owner, ref_date: date = None):
        budgets = Budget.objects.filter(owner=owner).select_related("category", "currency")
        return [b.to_dict(spent_base=BudgetService.compute_spent(b, ref_date)) for b in budgets]
