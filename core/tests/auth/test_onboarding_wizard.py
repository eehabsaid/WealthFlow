import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.authentication.services import AuthWorkflowService
from core.models import BalanceEntry, Company, Currency, Expense, ExpenseCategory
from core.services.onboarding import DEFAULT_EXPENSE_CATEGORIES

User = get_user_model()


class OnboardingWizardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="newbie", password="pw12345")
        self.client.force_login(self.user)

    def _complete(self, payload):
        return self.client.post("/api/onboarding/complete/", data=json.dumps(payload), content_type="application/json")

    def test_new_user_gets_default_categories_and_needs_wizard(self):
        self.assertEqual(ExpenseCategory.objects.filter(owner=self.user).count(), len(DEFAULT_EXPENSE_CATEGORIES))
        status = self.client.get("/api/onboarding/status/").json()
        self.assertTrue(status["needs_wizard"])
        self.assertTrue(status["currencies"])

    def test_existing_profiles_are_marked_done_by_default_only_for_new_flag(self):
        profile = AuthWorkflowService.get_profile(self.user)
        self.assertFalse(profile.onboarding_completed)

    def test_complete_creates_employer_cash_entry_and_syncs_categories(self):
        usd = Currency.objects.filter(owner=self.user, code="USD").first()
        res = self._complete({
            "employer": {"name": "Acme"},
            "account": {"title": "Wallet", "currency_id": usd.id, "amount": "1500.50"},
            "categories": ["Groceries", "Pets"],
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Company.objects.filter(owner=self.user, name="Acme").exists())
        entry = BalanceEntry.objects.get(owner=self.user)
        self.assertEqual((entry.balance_type, entry.amount, entry.bank), ("cash", Decimal("1500.50"), None))
        names = set(ExpenseCategory.objects.filter(owner=self.user).values_list("name", flat=True))
        self.assertEqual(names, {"Groceries", "Pets"})
        self.assertFalse(self.client.get("/api/onboarding/status/").json()["needs_wizard"])

    def test_skip_creates_nothing_and_marks_done(self):
        self.assertEqual(self._complete({"skip": True}).status_code, 200)
        self.assertFalse(BalanceEntry.objects.filter(owner=self.user).exists())
        self.assertFalse(self.client.get("/api/onboarding/status/").json()["needs_wizard"])

    def test_cannot_use_another_users_currency_or_negative_amount(self):
        other = User.objects.create_user(username="other", password="pw12345")
        foreign = Currency.objects.filter(owner=other).first()
        self.assertEqual(self._complete({"account": {"currency_id": foreign.id, "amount": "5"}}).status_code, 400)
        mine = Currency.objects.filter(owner=self.user).first()
        self.assertEqual(self._complete({"account": {"currency_id": mine.id, "amount": "-5"}}).status_code, 400)
        self.assertFalse(BalanceEntry.objects.exists())
        self.assertTrue(self.client.get("/api/onboarding/status/").json()["needs_wizard"])

    def test_unauthenticated_is_rejected(self):
        self.client.logout()
        self.assertIn(self.client.get("/api/onboarding/status/").status_code, (401, 302))

    def test_wizard_cash_entry_lets_an_expense_deduct(self):
        mine = Currency.objects.filter(owner=self.user, code="EGP").first()
        self._complete({"account": {"currency_id": mine.id, "amount": "100"}})
        cat = ExpenseCategory.objects.filter(owner=self.user).first()
        res = self.client.post("/api/expenses/", data=json.dumps({
            "title": "Lunch", "amount": "40", "payment_method": "cash", "category_id": cat.id,
            "currency_id": mine.id, "date": "2026-09-20",
        }), content_type="application/json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(BalanceEntry.objects.get(owner=self.user).amount, Decimal("60.00"))
        self.assertTrue(Expense.objects.filter(owner=self.user).exists())
