"""Owner isolation, field/lookup validation and aggregation of the generic data tools."""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.test import TestCase

from core.services.ai.investigation import data_tools as dt
from core.services.ai.investigation import scope
from core.models import (
    AssetAcquisitionCost,
    AssetFurniture,
    AssetRenovation,
    BalanceEntry,
    Bank,
    BankCertificate,
    BankCertificateInterestHistory,
    Currency,
    Expense,
    FixedAsset,
    RealEstateDetails,
    SalaryEntry,
)

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
                     "AIMessage", "AIConversation", "AIKnowledgeEntry", "Document", "PlanPrice"):
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
        self.assertEqual(scope.resolve_model("Certificate").name, "BankCertificate")

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

    def test_model_catalog_exposes_complete_fields_and_foreign_key_search_paths(self):
        listing = {m["model"]: m for m in dt.models(self.a, {})["models"]}
        self.assertIn("amount_base", listing["Expense"]["fields"])
        self.assertIn("paid", listing["SalaryEntry"]["fields"])
        self.assertIn("AssetFurniture", listing)
        self.assertIn("AssetAcquisitionCost", listing)
        self.assertIn("RealEstateDetails", listing)

        expense = dt.models(self.a, {"model": "Expense"})
        fields = {field["name"]: field for field in expense["fields"]}
        self.assertIn("code", fields["currency"]["related_fields"])
        self.assertIn("name", fields["bank"]["related_fields"])
        self.assertIn("amount_base", expense["note"])

        certificate = dt.models(self.a, {"model": "Certificate"})
        self.assertEqual(certificate["model"], "BankCertificate")
        self.assertIn("interest_value", certificate["note"])
        history = dt.models(self.a, {"model": "BankCertificateInterestHistory"})
        self.assertIn("interest_amount", history["note"])

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

    def test_foreign_key_errors_suggest_related_field_paths(self):
        res = self.q(self.a, model="Expense", filters={"currency__iexact": "EGP"})
        self.assertIn("currency__code__iexact", res["error"])
        self.assertIn("bank__name__icontains", res["error"])

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

    def test_composite_grouping_and_having_find_duplicate_expense_rows(self):
        tenant = seed_tenant(self.a, "D", expenses=0)
        for index in range(2):
            Expense.objects.create(
                owner=self.a,
                date=datetime.date(2026, 9, 10),
                year=2026,
                month=9,
                category=tenant["category"],
                amount=Decimal("25.00"),
                amount_base=Decimal("25.00"),
                currency=tenant["currency"],
                bank=tenant["bank"],
                description=f"duplicate candidate {index}",
            )

        duplicates = self.q(
            self.a,
            model="Expense",
            group_by="date,amount_base,category",
            aggregate={"count": "*"},
            having={"count__gt": 1},
        )
        self.assertEqual(duplicates["group_count"], 1)
        self.assertEqual(sum(row["count"] for row in duplicates["groups"]), 2)

    def test_actual_expense_query_shape_distinguishes_base_and_transaction_currency(self):
        tenant = seed_tenant(self.a, "X", expenses=0)
        euro = Currency.objects.create(owner=self.a, code="EUR", name="Euro")
        Expense.objects.create(
            owner=self.a,
            date=datetime.date(2026, 9, 10),
            year=2026,
            month=9,
            category=tenant["category"],
            amount=Decimal("100.00"),
            amount_base=Decimal("150.00"),
            currency=euro,
            bank=tenant["bank"],
        )

        base_total = self.q(
            self.a,
            model="Expense",
            filters={"category__name__iexact": "Cat X", "date__year": 2026},
            aggregate={"count": "*", "sum": "amount_base"},
        )
        source_total = self.q(
            self.a,
            model="Expense",
            filters={"category__name__iexact": "Cat X", "date__year": 2026},
            aggregate={"sum": "amount"},
        )
        self.assertEqual(base_total["result"]["count"], 1)
        self.assertEqual(Decimal(base_total["result"]["sum_amount_base"]), Decimal("150.00"))
        self.assertEqual(Decimal(source_total["result"]["sum_amount"]), Decimal("100.00"))

    def test_actual_bank_and_certificate_queries_use_related_currency_fields(self):
        bank = Bank.objects.get(owner=self.a, name="Bank A")
        egp, _ = Currency.objects.get_or_create(
            owner=self.a, code="EGP", defaults={"name": "Egyptian Pound"}
        )
        BalanceEntry.objects.create(
            owner=self.a, title="cash", balance_type="cash", bank=bank, currency=egp, amount=Decimal("1000.00")
        )
        BalanceEntry.objects.create(
            owner=self.a, title="bank", balance_type="bank", bank=bank, currency=egp, amount=Decimal("200.00")
        )
        balance = self.q(
            self.a,
            model="BalanceEntry",
            filters={
                "bank__name__icontains": "Bank A",
                "currency__code__iexact": "EGP",
                "balance_type__in": ["cash", "bank"],
            },
            aggregate={"count": "*", "sum": "amount"},
        )
        self.assertEqual(balance["result"]["count"], 2)
        self.assertEqual(Decimal(balance["result"]["sum_amount"]), Decimal("1200.00"))
        grouped = self.q(
            self.a,
            model="BalanceEntry",
            group_by="currency__code",
            aggregate={"sum": "amount"},
        )
        self.assertEqual(grouped["groups"][0]["currency__code"], "EGP")
        self.assertEqual(Decimal(grouped["groups"][0]["sum_amount"]), Decimal("1200.00"))

        certificate = BankCertificate.objects.create(
            owner=self.a, bank=bank, currency=egp, amount=Decimal("1000.00")
        )
        BankCertificateInterestHistory.objects.create(
            certificate=certificate,
            posting_date=datetime.date(2023, 4, 1),
            posting_period="2023-04",
            bank=bank,
            currency=egp,
            interest_amount=Decimal("15.00"),
        )
        interest = self.q(
            self.a,
            model="BankCertificateInterestHistory",
            filters={"currency__code__iexact": "EGP", "posting_date__year": 2023},
            aggregate={"count": "*", "sum": "interest_amount"},
        )
        self.assertEqual(interest["result"]["count"], 1)
        self.assertEqual(Decimal(interest["result"]["sum_interest_amount"]), Decimal("15.00"))

    def test_actual_salary_and_asset_queries_use_their_own_models_and_fields(self):
        salary = SalaryEntry.objects.get(company__owner=self.a)
        salary.year, salary.month = 2026, "September"
        salary.expected, salary.paid = Decimal("1000.00"), Decimal("800.00")
        salary.save()
        salary_total = self.q(
            self.a,
            model="SalaryEntry",
            filters={"year": 2026, "month": "September"},
            aggregate={"sum": "expected", "count": "*"},
        )
        self.assertEqual(salary_total["result"]["count"], 1)
        self.assertEqual(Decimal(salary_total["result"]["sum_expected"]), Decimal("1000.00"))

        asset = FixedAsset.objects.get(owner=self.a)
        AssetFurniture.objects.bulk_create([
            AssetFurniture(asset=asset, name="Sofa", amount_base=Decimal("100.00"), amount_usd=Decimal("10.00"))
        ])
        AssetAcquisitionCost.objects.bulk_create([
            AssetAcquisitionCost(asset=asset, category="Fees", amount_base=Decimal("200.00"), amount_usd=Decimal("20.00"))
        ])
        AssetRenovation.objects.create(
            asset=asset,
            date=datetime.date(2026, 9, 10),
            category="Kitchen",
            amount_base=Decimal("54848.25"),
        )
        RealEstateDetails.objects.create(asset=asset, last_estimated_market_price=Decimal("50000.00"))

        furniture = self.q(self.a, model="AssetFurniture", aggregate={"sum": "amount_usd", "count": "*"})
        acquisition = self.q(self.a, model="AssetAcquisitionCost", aggregate={"sum": "amount_base"})
        renovation = self.q(
            self.a,
            model="AssetRenovation",
            filters={"asset__name__iexact": "Asset A"},
            aggregate={"sum": "amount_base", "count": "*"},
        )
        details = self.q(self.a, model="RealEstateDetails", aggregate={"count": "*"})
        self.assertEqual(Decimal(furniture["result"]["sum_amount_usd"]), Decimal("10.00"))
        self.assertEqual(Decimal(acquisition["result"]["sum_amount_base"]), Decimal("200.00"))
        self.assertEqual(renovation["result"]["count"], 1)
        self.assertEqual(Decimal(renovation["result"]["sum_amount_base"]), Decimal("54848.25"))
        self.assertEqual(details["result"]["count"], 1)

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
