import importlib
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.apps import apps as django_apps
from core.models import Currency, BalanceEntry, Bank

User = get_user_model()


class VerifyRepointTest(TestCase):
    def test_simulated_legacy_data_gets_repointed(self):
        # Simulate a real pre-migration deployment: a template EGP row
        # already exists (owner=None) before this user is created.
        Currency.objects.get_or_create(owner=None, code="EGP", defaults={"name": "Egyptian Pound"})

        u = User.objects.create_user(username="legacy_user", password="pw12345")
        user_egp = Currency.objects.filter(owner=u, code="EGP").first()
        template_egp = Currency.objects.filter(owner=None, code="EGP").first()
        self.assertIsNotNone(user_egp)
        self.assertIsNotNone(template_egp)
        self.assertNotEqual(user_egp.id, template_egp.id)

        bank = Bank.objects.create(owner=u, name="Test Bank")
        entry = BalanceEntry.objects.create(
            owner=u, bank=bank, currency=template_egp, amount=100,
            balance_type=BalanceEntry.BalanceType.CASH,
        )
        entry.refresh_from_db()
        self.assertEqual(entry.currency_id, template_egp.id)

        mod = importlib.import_module("core.migrations.0015_repoint_currency_fks")
        mod.repoint_currency_fks(django_apps, None)

        entry.refresh_from_db()
        self.assertEqual(entry.currency_id, user_egp.id)
        self.assertNotEqual(entry.currency_id, template_egp.id)
