from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core.models import Currency, Expense, ExchangeRate
from core.services.shared.base_currency import get_user_base_code, set_user_base_currency

User = get_user_model()


@override_settings(MULTI_CURRENCY_ENABLED=True)
class SetBaseCurrencyRollbackTests(TestCase):
    """A user's own expense can be posted in a currency that has no stored
    market rate (e.g. a one-off historical entry). Switching the user's
    default must not silently corrupt that expense's amount_egp — the whole
    change rolls back instead."""

    def setUp(self):
        self.user = User.objects.create_user(username="rollback_user", password="pw12345")
        self.egp, _ = Currency.objects.get_or_create(owner=self.user, code="EGP", defaults={"symbol": "EGP", "name": "EGP", "order": 0})
        self.sar, _ = Currency.objects.get_or_create(owner=self.user, code="SAR", defaults={"symbol": "SAR", "name": "SAR", "order": 1})
        self.jpy, _ = Currency.objects.get_or_create(owner=self.user, code="JPY", defaults={"symbol": "JPY", "name": "JPY", "order": 2})
        ExchangeRate.objects.create(currency_code="SAR", buy_rate=Decimal("13.00"), sell_rate=Decimal("13.00"), mid_rate=Decimal("13.00"))
        # No ExchangeRate for JPY on purpose.

    def test_switch_is_refused_and_nothing_changes_when_an_existing_entry_has_no_rate(self):
        exp = Expense.objects.create(owner=self.user, date="2026-01-01", year=2026, month=1, currency=self.jpy, amount=Decimal("1000"), amount_egp=Decimal("530"))
        with self.assertRaises(ValueError):
            set_user_base_currency(self.user, "SAR")
        exp.refresh_from_db()
        self.assertEqual(exp.amount_egp, Decimal("530"))  # untouched
        self.assertEqual(get_user_base_code(self.user), "EGP")  # profile not switched either

    def test_switch_succeeds_and_persists_when_every_entry_has_a_rate(self):
        Expense.objects.create(owner=self.user, date="2026-01-01", year=2026, month=1, currency=self.egp, amount=Decimal("130"), amount_egp=Decimal("130"))
        set_user_base_currency(self.user, "SAR")
        self.assertEqual(get_user_base_code(self.user), "SAR")
