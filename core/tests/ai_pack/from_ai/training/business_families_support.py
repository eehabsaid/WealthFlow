"""Shared base for the business family tests."""


import random
from decimal import Decimal

from django.test import TestCase

from ai.training.services import phrasing
from core.models import (
    BalanceEntry,
    Currency,
    FixedAsset,
    SalaryEntry,
)
from core.services.shared.base_currency import get_user_base_code
from core.tests.ai_pack.investigation.support import make_user, seed_tenant


class BusinessFamilyBase(TestCase):
    def setUp(self):
        self.user = make_user("business_families")
        tenant = seed_tenant(self.user, "BF", expenses=0)
        base_code = str(get_user_base_code(self.user)).upper()
        self.currency, _ = Currency.objects.get_or_create(
            owner=self.user, code=base_code, defaults={"name": "Base currency"}
        )
        self.bank = tenant["bank"]
        self.category = tenant["category"]
        self.company = tenant["company"]
        self.company.current_salary_currency = self.currency
        self.company.save(update_fields=["current_salary_currency"])
        self.salary = SalaryEntry.objects.get(company=self.company)
        self.salary.year, self.salary.month = 2025, "1"
        self.salary.expected, self.salary.paid, self.salary.bonus = (
            Decimal("1000.00"), Decimal("800.00"), Decimal("50.00")
        )
        self.salary.save()

        self.asset = FixedAsset.objects.get(owner=self.user)
        self.asset.name = "Rental asset BF"
        self.asset.status = "Owned"
        self.asset.current_market_value = Decimal("50000.00")
        self.asset.save()
        BalanceEntry.objects.create(
            owner=self.user, title="Bank balance", balance_type="bank", bank=self.bank,
            currency=self.currency, amount=Decimal("500.00"),
        )

    @staticmethod
    def _cases(module, method, user):
        return getattr(module, method)(user, phrasing.LANGS, random.Random(1))

    def _assert_four_languages(self, cases, key):
        found = [case for case in cases if case.key.startswith(key)]
        self.assertEqual({case.meta["lang"] for case in found}, set(phrasing.LANGS))
        self.assertTrue(all(case.question for case in found))
        return next(case for case in found if case.meta["lang"] == "en" and "|" not in case.key)
