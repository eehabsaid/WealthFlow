from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Bank, Currency, Expense, ExpenseCategory, ExpenseSubcategory
from core.services.expenses.expense_filters import apply_expense_filters

User = get_user_model()


class ExpenseFilterServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner_a", password="pw")
        self.food = ExpenseCategory.objects.create(
            owner=self.user, name="Food & Drinks", icon="x", color_hex="#111111", order=1
        )
        self.coffee = ExpenseSubcategory.objects.create(category=self.food, name="Coffee Shops", order=1)
        self.bank = Bank.objects.create(owner=self.user, name="Main Bank")
        self.e1 = Expense.objects.create(
            owner=self.user, date=date(2026, 1, 15), year=2026, month=1, amount=100,
            amount_base=100, category=self.food, subcategory=self.coffee, bank=self.bank,
            payment_method="Card", description="Morning latte", notes="office visit",
        )
        self.e2 = Expense.objects.create(
            owner=self.user, date=date(2026, 2, 20), year=2026, month=2, amount=250,
            amount_base=250, category=self.food, payment_method="Cash", description="Groceries",
        )
        self.qs = Expense.objects.all()

    def ids(self, qs):
        return sorted(qs.values_list("id", flat=True))

    def test_search_description(self):
        self.assertEqual(self.ids(apply_expense_filters(self.qs, {"search": "LATTE"})), [self.e1.id])

    def test_search_notes(self):
        self.assertEqual(self.ids(apply_expense_filters(self.qs, {"search": "office"})), [self.e1.id])

    def test_search_category_name(self):
        self.assertEqual(sorted(self.ids(apply_expense_filters(self.qs, {"search": "food"}))), [self.e1.id, self.e2.id])

    def test_search_subcategory_name(self):
        self.assertEqual(self.ids(apply_expense_filters(self.qs, {"search": "coffee"})), [self.e1.id])

    def test_search_bank_name(self):
        self.assertEqual(self.ids(apply_expense_filters(self.qs, {"search": "main bank"})), [self.e1.id])

    def test_search_payment_method(self):
        self.assertEqual(self.ids(apply_expense_filters(self.qs, {"search": "cash"})), [self.e2.id])

    def test_search_no_match(self):
        self.assertEqual(list(apply_expense_filters(self.qs, {"search": "zzz"})), [])

    def test_filter_year_month(self):
        self.assertEqual(self.ids(apply_expense_filters(self.qs, {"year": "2026", "month": "2"})), [self.e2.id])

    def test_filter_category_and_subcategory(self):
        self.assertEqual(self.ids(apply_expense_filters(self.qs, {"category": self.food.id})), [self.e1.id, self.e2.id])
        self.assertEqual(self.ids(apply_expense_filters(self.qs, {"subcategory": self.coffee.id})), [self.e1.id])

    def test_subcategory_must_belong_to_selected_category(self):
        other = ExpenseCategory.objects.create(
            owner=self.user, name="Travel", icon="x", color_hex="#222222", order=2
        )
        other_sub = ExpenseSubcategory.objects.create(category=other, name="Flights", order=1)
        # Subcategory of another category + that category selected: no match.
        self.assertEqual(
            list(apply_expense_filters(self.qs, {"category": other.id, "subcategory": self.coffee.id})),
            [],
        )
        # Subcategory of the selected category: matches.
        self.assertEqual(
            self.ids(apply_expense_filters(self.qs, {"category": self.food.id, "subcategory": self.coffee.id})),
            [self.e1.id],
        )
        # No category selected: subcategory filter works as before.
        self.assertEqual(
            self.ids(apply_expense_filters(self.qs, {"subcategory": other_sub.id})),
            [],
        )

    def test_filter_bank_and_payment_method(self):
        self.assertEqual(self.ids(apply_expense_filters(self.qs, {"bank": self.bank.id})), [self.e1.id])
        self.assertEqual(self.ids(apply_expense_filters(self.qs, {"payment_method": "Card"})), [self.e1.id])

    def test_filter_date_range(self):
        self.assertEqual(
            self.ids(apply_expense_filters(self.qs, {"start": "2026-02-01", "end": "2026-02-28"})), [self.e2.id]
        )

    def test_filter_amount_min_max(self):
        self.assertEqual(self.ids(apply_expense_filters(self.qs, {"amount_min": "200"})), [self.e2.id])
        self.assertEqual(self.ids(apply_expense_filters(self.qs, {"amount_max": "150"})), [self.e1.id])
        self.assertEqual(
            sorted(self.ids(apply_expense_filters(self.qs, {"amount_min": "50", "amount_max": "300"}))),
            [self.e1.id, self.e2.id],
        )

    def test_combined_filters_and_search(self):
        self.assertEqual(
            self.ids(apply_expense_filters(self.qs, {"bank": self.bank.id, "amount_min": "50", "search": "latte"})),
            [self.e1.id],
        )
        self.assertEqual(
            list(apply_expense_filters(self.qs, {"bank": self.bank.id, "search": "groceries"})), []
        )

    def test_malformed_dates_ignored(self):
        for bad in ("2026-13-99", "2026-02-30", "not-a-date", "banana", "2026-00-10"):
            with self.subTest(bad=bad):
                qs = apply_expense_filters(self.qs, {"start": bad, "end": bad})
                self.assertEqual(sorted(self.ids(qs)), [self.e1.id, self.e2.id])

    def test_invalid_params_ignored(self):
        self.assertEqual(
            sorted(self.ids(apply_expense_filters(self.qs, {
                "year": "abc", "month": "", "category": "x", "subcategory": "1e3",
                "bank": "?", "start": "not-a-date", "end": "banana", "amount_min": "NaN",
                "amount_max": "Infinity", "search": "   ",
            }))),
            [self.e1.id, self.e2.id],
        )


class ExpenseListEndpointFilterTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner_a", password="pw")
        self.other = User.objects.create_user(username="owner_b", password="pw")
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.food = ExpenseCategory.objects.create(
            owner=self.user, name="Food", icon="x", color_hex="#111111", order=1
        )
        self.bank = Bank.objects.create(owner=self.user, name="My Bank")
        self.e = Expense.objects.create(
            owner=self.user, date=date(2026, 3, 10), year=2026, month=3, amount=75,
            amount_base=75, category=self.food, bank=self.bank, payment_method="Card",
            currency=self.currency,
            description="Taxi ride",
        )
        self.other_food = ExpenseCategory.objects.create(owner=self.other, name="Snacks", order=1)
        self.other_e = Expense.objects.create(
            owner=self.other, date=date(2026, 3, 11), year=2026, month=3, amount=40,
            amount_base=40, category=self.other_food, description="Chips",
            currency=self.currency,
        )

    def get(self, params):
        return self.client.get(f"/api/expenses/{params}")

    def items(self, data):
        if isinstance(data, dict) and "entries" in data:
            return data["entries"]
        return data

    def test_requires_authentication(self):
        self.client.logout()
        self.assertEqual(self.get("?").status_code, 401)

    def test_search_and_filters_return_only_matching_own_expenses(self):
        self.client.force_login(self.user)
        url = "?search=taxi&payment_method=Card&bank={}&amount_min=50&start=2026-03-01&end=2026-03-31".format(self.bank.id)
        data = self.get(url).json()
        items = self.items(data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["description"], "Taxi ride")

    def test_ownership_isolation_with_filters(self):
        self.client.force_login(self.other)
        data = self.get("?search=chips").json()
        items = self.items(data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], self.other_e.id)
        data = self.get("?search=taxi").json()
        self.assertEqual(len(self.items(data)), 0)
