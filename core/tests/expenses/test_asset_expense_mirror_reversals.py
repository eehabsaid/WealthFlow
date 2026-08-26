from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import (
    AssetAcquisitionCost,
    AssetRenovation,
    BalanceEntry,
    Currency,
    Expense,
    ExpenseCategory,
    FixedAsset,
)

User = get_user_model()


class AssetExpenseMirrorReversalsTest(TestCase):
    def setUp(self):
        self.asset = FixedAsset.objects.create(
            name="Nile View Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2025, 1, 1),
            purchase_price=1000000,
            current_market_value=1200000,
        )
        self.currency_egp, _ = Currency.objects.get_or_create(
            code="EGP", defaults={"symbol": "£", "name": "Egyptian Pound"}
        )

    def _fixed_assets_category(self):
        return ExpenseCategory.objects.filter(name="Fixed Assets").first()

    def test_mirroring_never_touches_balance(self):
        cash_entry = BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=self.currency_egp,
            amount=100000,
        )
        AssetRenovation.objects.create(
            asset=self.asset,
            date=date(2025, 3, 10),
            category="Painting",
            amount_egp=5000,
            payment_method="Cash",
        )
        cash_entry.refresh_from_db()
        # Direct ORM create bypasses the balance-affecting CRUD view/service,
        # exactly like the mirror signal does - confirms mirroring itself
        # carries no balance side effect of its own.
        self.assertEqual(cash_entry.amount, Decimal("100000"))

    def test_manual_expense_still_fully_editable(self):
        from core.services import ExpenseService

        BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=self.currency_egp,
            amount=50000,
        )
        exp = ExpenseService.create_expense(
            {
                "date": "2025-03-01",
                "amount": 1000,
                "payment_method": "Cash",
            }
        )
        self.assertFalse(exp.is_readonly_mirror)
        updated = ExpenseService.update_expense(exp.id, {"amount": 1200})
        self.assertEqual(updated.amount, Decimal("1200"))
        ExpenseService.delete_expense(exp.id)
        self.assertFalse(Expense.objects.filter(pk=exp.id).exists())

    def test_adding_one_renovation_does_not_recreate_other_mirrors(self):
        """The whole-asset save resubmits ALL renovations together, so
        without id-matching every mirror would get a new id/created_at on
        every save (looking like everything was "reinserted"). With
        stable-id update-or-create, only genuinely new/changed rows churn."""
        from core.services.fixed_assets.asset_cost_sync_service import _sync_asset_renovations

        BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=self.currency_egp,
            amount=1000000,
        )
        _sync_asset_renovations(self.asset, [
            {"date": "2025-01-10", "category": "Painting", "amount_egp": 5000},
        ])
        existing_renovation = AssetRenovation.objects.get(asset=self.asset)
        mirror_before = Expense.objects.get(source_type="asset_renovation", source_id=existing_renovation.id)

        # Simulate the UI resubmitting the full list (existing item now
        # carrying its id, as the fixed frontend does) plus one new item.
        _sync_asset_renovations(self.asset, [
            {
                "id": existing_renovation.id,
                "date": "2025-01-10",
                "category": "Painting",
                "amount_egp": 5000,
            },
            {"date": "2025-02-05", "category": "Flooring", "amount_egp": 9000},
        ])

        self.assertEqual(AssetRenovation.objects.filter(asset=self.asset).count(), 2)
        self.assertEqual(Expense.objects.filter(source_type="asset_renovation").count(), 2)
        mirror_after = Expense.objects.get(source_type="asset_renovation", source_id=existing_renovation.id)
        self.assertEqual(mirror_after.id, mirror_before.id)
        self.assertEqual(mirror_after.created_at, mirror_before.created_at)

    def test_adding_one_acquisition_cost_does_not_recreate_other_mirrors(self):
        from core.services.fixed_assets.asset_cost_sync_service import _sync_asset_acquisition_costs

        BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=self.currency_egp,
            amount=1000000,
        )
        _sync_asset_acquisition_costs(self.asset, [
            {"date": "2025-01-05", "category": "Lawyer Fees", "amount_egp": 25000},
        ])
        existing_cost = AssetAcquisitionCost.objects.get(asset=self.asset)
        mirror_before = Expense.objects.get(source_type="asset_acquisition_cost", source_id=existing_cost.id)

        _sync_asset_acquisition_costs(self.asset, [
            {
                "id": existing_cost.id,
                "date": "2025-01-05",
                "category": "Lawyer Fees",
                "amount_egp": 25000,
            },
            {"date": "2025-02-01", "category": "Registration Fees", "amount_egp": 3000},
        ])

        self.assertEqual(AssetAcquisitionCost.objects.filter(asset=self.asset).count(), 2)
        self.assertEqual(Expense.objects.filter(source_type="asset_acquisition_cost").count(), 2)
        mirror_after = Expense.objects.get(source_type="asset_acquisition_cost", source_id=existing_cost.id)
        self.assertEqual(mirror_after.id, mirror_before.id)

    def test_removing_a_renovation_deletes_only_its_mirror(self):
        from core.services.fixed_assets.asset_cost_sync_service import _sync_asset_renovations

        BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=self.currency_egp,
            amount=1000000,
        )
        _sync_asset_renovations(self.asset, [
            {"date": "2025-01-10", "category": "Painting", "amount_egp": 5000},
            {"date": "2025-02-05", "category": "Flooring", "amount_egp": 9000},
        ])
        renovations = list(AssetRenovation.objects.filter(asset=self.asset).order_by("id"))
        keep_id = renovations[1].id

        # Resubmit with only the second item kept (first removed by the user)
        _sync_asset_renovations(self.asset, [
            {
                "id": keep_id,
                "date": "2025-02-05",
                "category": "Flooring",
                "amount_egp": 9000,
            },
        ])

        self.assertEqual(AssetRenovation.objects.filter(asset=self.asset).count(), 1)
        self.assertEqual(Expense.objects.filter(source_type="asset_renovation").count(), 1)
        self.assertTrue(
            Expense.objects.filter(source_type="asset_renovation", source_id=keep_id).exists()
        )
