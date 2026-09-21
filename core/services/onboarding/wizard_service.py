"""First-run setup wizard: status + one-shot completion."""

from decimal import Decimal, InvalidOperation

from django.db import transaction

from core.authentication.services import AuthWorkflowService
from core.models import BalanceEntry, Company, Currency, Expense, ExchangeRate, ExpenseCategory
from core.services.onboarding.default_categories import DEFAULT_EXPENSE_CATEGORIES
from core.services.shared.base_currency import get_user_base_code, multi_currency_enabled, set_user_base_currency


class OnboardingService:
    @staticmethod
    def status(user):
        profile = AuthWorkflowService.get_profile(user)
        return {
            "needs_wizard": not profile.onboarding_completed,
            "rates_missing": not ExchangeRate.objects.exists(),
            "default_currency": get_user_base_code(user),
            "multi_currency_enabled": multi_currency_enabled(),
            "currencies": [
                {"id": c.id, "code": c.code, "symbol": c.symbol}
                for c in Currency.objects.filter(owner=user).order_by("order", "code")
            ],
            "categories": [
                {"name": c.name, "icon": c.icon}
                for c in ExpenseCategory.objects.filter(owner=user)
            ],
        }

    @staticmethod
    def _parse_amount(raw):
        try:
            amount = Decimal(str(raw if raw not in (None, "") else 0))
        except InvalidOperation:
            raise ValueError("invalid_amount")
        if amount < 0 or amount > Decimal("999999999999"):
            raise ValueError("invalid_amount")
        return amount

    @classmethod
    def _create_employer(cls, user, employer):
        name = str((employer or {}).get("name") or "").strip()[:200]
        if name:
            Company.objects.get_or_create(
                owner=user, name=name, defaults={"display_name": name}
            )

    @classmethod
    def _create_cash_account(cls, user, account):
        if not account:
            return
        currency = Currency.objects.filter(owner=user, id=account.get("currency_id")).first()
        if currency is None:
            raise ValueError("invalid_currency")
        title = str(account.get("title") or "").strip()[:200] or "Cash"
        BalanceEntry.objects.create(
            owner=user, title=title, currency=currency,
            balance_type=BalanceEntry.BalanceType.CASH,
            amount=cls._parse_amount(account.get("amount")),
        )

    @classmethod
    def _sync_categories(cls, user, names):
        """Keep exactly the chosen names; unchecked defaults are removed unless
        an expense already uses them."""
        wanted = [str(n).strip()[:100] for n in names if str(n).strip()]
        used = set(Expense.objects.filter(owner=user).values_list("category__name", flat=True))
        for cat in ExpenseCategory.objects.filter(owner=user):
            if cat.name not in wanted and cat.name not in used:
                cat.delete()
        defaults = {d["name"]: d for d in DEFAULT_EXPENSE_CATEGORIES}
        for order, name in enumerate(wanted, start=1):
            spec = defaults.get(name, {})
            ExpenseCategory.objects.get_or_create(
                owner=user, name=name,
                defaults={"icon": spec.get("icon", "💰"), "color_hex": spec.get("color_hex", "#0d6efd"), "order": order},
            )

    @classmethod
    @transaction.atomic
    def complete(cls, user, data):
        if not data.get("skip"):
            if data.get("default_currency"):
                set_user_base_currency(user, data["default_currency"])
            cls._create_employer(user, data.get("employer"))
            cls._create_cash_account(user, data.get("account"))
            if isinstance(data.get("categories"), list):
                cls._sync_categories(user, data["categories"])
        profile = AuthWorkflowService.get_profile(user)
        profile.onboarding_completed = True
        profile.save(update_fields=["onboarding_completed"])
