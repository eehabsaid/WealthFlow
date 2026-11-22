"""Shared fixtures for the budget answer tests."""


from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Budget, Currency, Expense, ExchangeRate, ExpenseCategory
from ai.services.query_engine.spec import QueryRequest


User = get_user_model()
TODAY = date.today()


def _req(cap, metric="", **filters):
    return QueryRequest(capability=cap, metric=metric, filters=filters)


class _Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="qe_bud", password="pw-12345-x")
        self.other = User.objects.create_user(username="qe_bud_other", password="pw-12345-x")
        for code, rate in (("USD", "50"), ("SAR", "13.333333"), ("AED", "13.6")):
            ExchangeRate.objects.create(currency_code=code, currency_name=code, buy_rate=Decimal(rate),
                                        sell_rate=Decimal(rate), mid_rate=Decimal(rate))
        self.egp, _ = Currency.objects.get_or_create(owner=self.user, code="EGP", defaults={"name": "Egyptian Pound"})
        self.food, _ = ExpenseCategory.objects.get_or_create(owner=self.user, name="Food")

    def budget(self, owner=None, name="Food budget", amount=1000, category=None, **kw):
        return Budget.objects.create(owner=owner or self.user, name=name, category=category, period="monthly",
                                     amount=amount, amount_base=amount, currency=self.egp, **kw)

    def spend(self, amount, category=None):
        Expense.objects.create(owner=self.user, date=TODAY, year=TODAY.year, month=TODAY.month, category=category,
                               amount=amount, amount_base=amount, currency=self.egp)
