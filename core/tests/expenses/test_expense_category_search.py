from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Expense, ExpenseCategory, ExpenseSubcategory

User = get_user_model()


class ExpenseCategorySearchTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner_a", password="pw")
        self.other = User.objects.create_user(username="owner_b", password="pw")
        self.food = ExpenseCategory.objects.create(
            owner=self.user, name="Food & Drinks", icon="🍔", color_hex="#ff0000", order=90
        )
        self.sub = ExpenseSubcategory.objects.create(
            category=self.food, name="Coffee Shops", order=1
        )
        self.flights = ExpenseCategory.objects.create(
            owner=self.user, name="Flights", icon="🚗", color_hex="#0d6efd", order=91
        )
        self.expense = Expense.objects.create(
            owner=self.user,
            date=date(2026, 1, 1),
            year=2026,
            month=1,
            amount=100,
            category=self.food,
        )
        self.other_cat = ExpenseCategory.objects.create(
            owner=self.other, name="Their Cat", order=1
        )

    def get(self, params=""):
        return self.client.get(f"/api/expense-categories/{params}")

    def test_requires_authentication(self):
        self.client.logout()
        self.assertEqual(self.get().status_code, 401)

    def test_multi_tenancy_isolation(self):
        self.client.force_login(self.other)
        data = self.get().json()
        names = [c["name"] for c in data["categories"]]
        self.assertIn("Their Cat", names)
        self.assertNotIn("Food & Drinks", names)
        self.assertEqual(
            data["total"], ExpenseCategory.objects.filter(owner=self.other).count()
        )

    def test_search_by_category_name_case_insensitive(self):
        self.client.force_login(self.user)
        data = self.get("?search=food").json()
        self.assertEqual([c["name"] for c in data["categories"]], ["Food & Drinks"])
        self.assertEqual(data["count"], 1)
        self.assertEqual(
            data["total"], ExpenseCategory.objects.filter(owner=self.user).count()
        )

    def test_search_by_subcategory_name(self):
        self.client.force_login(self.user)
        data = self.get("?search=coffee").json()
        self.assertEqual([c["name"] for c in data["categories"]], ["Food & Drinks"])
        self.assertEqual(
            [s["name"] for s in data["categories"][0]["subcategories"]], ["Coffee Shops"]
        )

    def test_search_no_match_returns_empty_list(self):
        self.client.force_login(self.user)
        data = self.get("?search=zzz").json()
        self.assertEqual(data["categories"], [])
        self.assertEqual(data["count"], 0)
        self.assertEqual(
            data["total"], ExpenseCategory.objects.filter(owner=self.user).count()
        )

    def test_usage_used_filters_to_categories_with_expenses(self):
        self.client.force_login(self.user)
        data = self.get("?usage=used").json()
        self.assertEqual([c["name"] for c in data["categories"]], ["Food & Drinks"])

    def test_usage_unused_filters_to_categories_without_expenses(self):
        self.client.force_login(self.user)
        data = self.get("?usage=unused").json()
        names = [c["name"] for c in data["categories"]]
        self.assertIn("Flights", names)
        self.assertNotIn("Food & Drinks", names)

    def test_search_and_usage_combine(self):
        self.client.force_login(self.user)
        data = self.get("?search=food&usage=unused").json()
        self.assertEqual(data["categories"], [])
        self.assertEqual(
            data["total"], ExpenseCategory.objects.filter(owner=self.user).count()
        )

    def test_response_shape_unchanged(self):
        self.client.force_login(self.user)
        data = self.get().json()
        self.assertEqual(
            len(data["categories"]),
            ExpenseCategory.objects.filter(owner=self.user).count(),
        )
        first = data["categories"][0]
        for key in ("id", "name", "icon", "color_hex", "order", "subcategories"):
            self.assertIn(key, first)

    def test_crud_still_works(self):
        self.client.force_login(self.user)
        res = self.client.post(
            "/api/expense-categories/",
            data='{"name": "Pets", "icon": "🐾"}',
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        pet = ExpenseCategory.objects.get(name="Pets")
        res = self.client.put(
            f"/api/expense-categories/{pet.id}/",
            data='{"name": "Pets & Birds"}',
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["name"], "Pets & Birds")
        res = self.client.delete(f"/api/expense-categories/{pet.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(ExpenseCategory.objects.filter(id=pet.id).exists())
