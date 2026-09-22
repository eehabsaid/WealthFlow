from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Company, Currency, Expense, ExchangeRate, PerDiem
from core.services.shared.base_currency_recalc import recalculate_base_amounts

User = get_user_model()


class BaseCurrencyRecalcTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="recalc_user", password="pw12345")
        self.egp, _ = Currency.objects.get_or_create(owner=self.user, code="EGP", defaults={"symbol": "EGP", "name": "EGP", "order": 0})
        self.sar, _ = Currency.objects.get_or_create(owner=self.user, code="SAR", defaults={"symbol": "SAR", "name": "SAR", "order": 1})
        ExchangeRate.objects.create(currency_code="SAR", buy_rate=Decimal("13.00"), sell_rate=Decimal("13.00"), mid_rate=Decimal("13.00"))

    def test_no_op_when_currency_does_not_actually_change(self):
        Expense.objects.create(owner=self.user, date="2026-01-01", year=2026, month=1, currency=self.egp, amount=Decimal("100"), amount_egp=Decimal("100"))
        moved = recalculate_base_amounts(self.user, "EGP", "egp")
        self.assertEqual(moved, 0)

    def test_expenses_are_recalculated_into_the_new_base(self):
        exp = Expense.objects.create(owner=self.user, date="2026-01-01", year=2026, month=1, currency=self.egp, amount=Decimal("130"), amount_egp=Decimal("130"))
        moved = recalculate_base_amounts(self.user, "EGP", "SAR")
        self.assertEqual(moved, 1)
        exp.refresh_from_db()
        self.assertEqual(exp.amount_egp, Decimal("10.00"))  # 130 EGP / 13 = 10 SAR

    def test_expenses_own_currency_is_never_changed_only_the_base_amount(self):
        exp = Expense.objects.create(owner=self.user, date="2026-01-01", year=2026, month=1, currency=self.egp, amount=Decimal("130"), amount_egp=Decimal("130"))
        recalculate_base_amounts(self.user, "EGP", "SAR")
        exp.refresh_from_db()
        self.assertEqual(exp.currency_id, self.egp.id)
        self.assertEqual(exp.amount, Decimal("130"))

    def test_per_diems_are_recalculated_into_the_new_base(self):
        company = Company.objects.create(owner=self.user, name="Acme", display_name="Acme", is_active=True)
        pd = PerDiem.objects.create(company=company, year=2026, date="2026-01-01", currency=self.egp, amount=Decimal("260"), amount_egp=Decimal("260"))
        moved = recalculate_base_amounts(self.user, "EGP", "SAR")
        self.assertEqual(moved, 1)
        pd.refresh_from_db()
        self.assertEqual(pd.amount_egp, Decimal("20.00"))  # 260 EGP / 13 = 20 SAR

    def test_missing_rate_raises_and_the_caller_can_roll_back(self):
        Expense.objects.create(owner=self.user, date="2026-01-01", year=2026, month=1, currency=self.egp, amount=Decimal("100"), amount_egp=Decimal("100"))
        with self.assertRaises(ValueError):
            recalculate_base_amounts(self.user, "EGP", "AED")  # AED has no stored ExchangeRate

    def test_only_the_requesting_users_rows_are_touched(self):
        other = User.objects.create_user(username="recalc_other", password="pw12345")
        other_egp, _ = Currency.objects.get_or_create(owner=other, code="EGP", defaults={"symbol": "EGP", "name": "EGP", "order": 0})
        other_exp = Expense.objects.create(owner=other, date="2026-01-01", year=2026, month=1, currency=other_egp, amount=Decimal("100"), amount_egp=Decimal("100"))
        Expense.objects.create(owner=self.user, date="2026-01-01", year=2026, month=1, currency=self.egp, amount=Decimal("130"), amount_egp=Decimal("130"))
        recalculate_base_amounts(self.user, "EGP", "SAR")
        other_exp.refresh_from_db()
        self.assertEqual(other_exp.amount_egp, Decimal("100"))
