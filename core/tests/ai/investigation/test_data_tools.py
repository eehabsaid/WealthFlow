"""Owner isolation, field/lookup validation and aggregation of the generic data tools."""

from __future__ import annotations

from django.test import TestCase

from core.services.ai.investigation import data_tools as dt
from core.services.ai.investigation import scope

from .support import make_user, seed_tenant


class ScopeCatalogTest(TestCase):
    def test_every_queryable_model_is_owner_scoped_or_global_reference_data(self):
        for name, info in scope.catalog().items():
            if info.scope is None:
                self.assertIn(name, scope.GLOBAL_MODELS, name)
            else:
                self.assertTrue(info.scope == "owner" or info.scope.endswith("__owner"), f"{name}: {info.scope}")

    def test_secret_and_internal_tables_are_never_queryable(self):
        for name in ("AppSettings", "AuthToken", "AuthAuditLog", "PagePermission", "UserRole", "UserProfile", "EmailTemplate",
                     "AIMessage", "AIConversation", "AIKnowledgeEntry", "AIModelVersion", "Document", "PlanPrice"):
            self.assertNotIn(name, scope.catalog(), name)
            self.assertIsNone(scope.resolve_model(name), name)

    def test_children_are_isolated_through_their_parent(self):
        info = scope.catalog()
        self.assertEqual(info["SalaryEntry"].scope, "company__owner")
        self.assertEqual(info["AssetRental"].scope, "asset__owner")
        self.assertEqual(info["ScenarioEvent"].scope, "scenario__owner")

    def test_name_resolution_is_forgiving(self):
        for alias in ("expense", "Expenses", "EXPENSE", "expenses "):
            self.assertEqual(scope.resolve_model(alias).name, "Expense")
        self.assertEqual(scope.resolve_model("fixed asset").name, "FixedAsset")
        self.assertEqual(scope.resolve_model("salary_entry").name, "SalaryEntry")

    def test_no_visible_field_looks_sensitive(self):
        for info in scope.catalog().values():
            for f in scope.visible_fields(info.model):
                self.assertFalse(scope.SENSITIVE_FIELD.search(f.name), f"{info.name}.{f.name}")


class DataToolsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a, cls.b = make_user("tenant_a"), make_user("tenant_b")
        seed_tenant(cls.a, "A", expenses=3, amount="10.00")
        seed_tenant(cls.b, "B", expenses=5, amount="100.00")

    def q(self, user, **params):
        return dt.query(user, params)

    def test_each_user_only_sees_own_rows_directly_and_through_parents(self):
        self.assertEqual(self.q(self.a, model="Expense")["total_matching"], 3)
        self.assertEqual(self.q(self.b, model="Expense")["total_matching"], 5)
        for model, mine in (("SalaryEntry", 1), ("FixedAsset", 1), ("Bank", 1), ("Company", 1)):
            self.assertEqual(self.q(self.a, model=model)["total_matching"], mine, model)
        rows = self.q(self.a, model="Expense", limit=100)["rows"]
        self.assertTrue(all("A expense" in r["description"] for r in rows))

    def test_filters_cannot_widen_the_scope(self):
        # an attacker-style filter naming the other tenant's data still starts from the caller's own rows
        res = self.q(self.a, model="Expense", filters={"amount__gte": "50"})
        self.assertEqual(res["total_matching"], 0)
        res = self.q(self.a, model="Expense", filters={"description__icontains": "B expense"})
        self.assertEqual(res["total_matching"], 0)
        res = self.q(self.a, model="Expense", filters={"bank__name": "Bank B"})
        self.assertEqual(res["total_matching"], 0)

    def test_catalog_counts_are_per_user(self):
        listing = {m["model"]: m["rows"] for m in dt.models(self.a, {})["models"]}
        self.assertEqual(listing["Expense"], 3)
        self.assertEqual(dt.models(self.b, {"model": "expense"})["rows"], 5)

    def test_relations_to_users_and_secrets_are_refused(self):
        for params in ({"filters": {"owner__username": "tenant_b"}}, {"fields": ["owner__password"]},
                       {"filters": {"owner__password__startswith": "pbkdf2"}}, {"order_by": ["owner__password"]},
                       {"aggregate": {"count": "owner__password"}}):
            res = self.q(self.a, model="Expense", **params)
            self.assertIn("error", res, params)
            self.assertNotIn("rows", res)

    def test_forbidden_models_report_the_queryable_list(self):
        res = self.q(self.a, model="AppSettings")
        self.assertIn("unknown model", res["error"])
        self.assertIn("Expense", res["error"])
        self.assertNotIn("AppSettings,", res["error"])

    def test_unknown_field_error_lists_valid_fields(self):
        res = self.q(self.a, model="Expense", filters={"bogus": 1})
        self.assertIn("unknown field 'bogus'", res["error"])
        self.assertIn("amount_base", res["error"])

    def test_aggregate_group_order_limit_and_filter_values(self):
        total = self.q(self.a, model="Expense", aggregate={"sum": "amount_base", "count": "*"})
        self.assertEqual((total["result"]["count"], float(total["result"]["sum_amount_base"])), (3, 30.0))
        grouped = self.q(self.a, model="Expense", aggregate={"sum": "amount_base"}, group_by="category__name")
        self.assertEqual([(g["category__name"], float(g["sum_amount_base"])) for g in grouped["groups"]], [("Cat A", 30.0)])
        dated = self.q(self.a, model="Expense", filters={"date__gte": "2026-09-02", "month": "9"}, order_by=["-date"], limit=1)
        self.assertEqual((dated["total_matching"], dated["returned"], str(dated["rows"][0]["date"])), (2, 1, "2026-09-03"))
        self.assertEqual(self.q(self.a, model="Expense", filters='{"year": 2026}')["total_matching"], 3)
        self.assertEqual(self.q(self.a, model="Expense", filters={"id__in": "1,2"})["total_matching"] <= 2, True)
        self.assertEqual(self.q(self.a, model="Expense", filters={"description__isnull": "false"})["total_matching"], 3)

    def test_bad_input_never_raises(self):
        for params in ({"filters": "{not json"}, {"filters": [1]}, {"aggregate": {"median": "amount"}}, {"aggregate": "sum"},
                       {"filters": {"date__gte": "not-a-date"}}, {"filters": {"amount__range": "1"}}, {"limit": "abc"},
                       {"group_by": "nope"}, {"fields": ["nope"]}):
            res = dt.query(self.a, {"model": "Expense", **params})
            self.assertIsInstance(res, dict, params)

    def test_limit_is_capped(self):
        self.assertLessEqual(self.q(self.b, model="Expense", limit=9999)["returned"], dt.MAX_ROWS)

    def test_global_market_tables_are_readable_by_anyone(self):
        self.assertNotIn("error", self.q(self.a, model="GoldPrice"))
        self.assertNotIn("error", self.q(self.b, model="ExchangeRate"))
