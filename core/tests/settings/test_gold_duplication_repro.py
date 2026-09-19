import importlib
from decimal import Decimal
from django.test import TestCase
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model

from core.models import Currency, BalanceEntry, FixedAsset
from core.models.fixed_assets_gold import GoldDetails
from core.services.fixed_assets.gold_sync_service import _sync_gold_balance_from_assets

User = get_user_model()


class GoldDuplicationRealisticRepro(TestCase):
    """Reproduces the exact sequence that caused Ehab's duplicate gold
    row: a legacy gold BalanceEntry created BEFORE the per-user catalog
    migration (pointing at the template Gold currency), then the
    balance-sync running AFTER the user had their own cloned Gold
    currency but BEFORE migration 0015 repointed existing records."""

    def setUp(self):
        Currency.objects.get_or_create(
            owner=None, code="Gold", defaults={"name": "Gold (grams)"}
        )
        self.user = User.objects.create_user(username="gold_user", password="pw12345")
        self.template_gold = Currency.objects.get(owner=None, code="Gold")
        self.user_gold = Currency.objects.get(owner=self.user, code="Gold")
        self.assertNotEqual(self.template_gold.id, self.user_gold.id)

        asset = FixedAsset.objects.create(
            owner=self.user, name="My Gold Bar", asset_type="Gold",
            status="Owned", purchase_date="2024-01-01", purchase_price=1000,
        )
        GoldDetails.objects.create(
            asset=asset, gold_type="Bar", purity="24k", weight=10, unit="gram",
        )

        # The legacy gold BalanceEntry, as it would have existed before
        # any of this per-user work landed — pointing at the template row.
        self.legacy_entry = BalanceEntry.objects.create(
            owner=self.user, title="Gold 24K", balance_type=BalanceEntry.BalanceType.GOLD,
            bank=None, currency_id=self.template_gold.id, purity="24k", amount=10,
        )

    def test_sync_before_repoint_creates_a_duplicate(self):
        """This documents the bug as it actually happened: syncing while
        the legacy entry still points at the template currency creates a
        SECOND row instead of updating the first, because the sync only
        looks for entries matching the user's OWN (different) currency id."""
        _sync_gold_balance_from_assets(self.user)

        gold_entries = BalanceEntry.objects.filter(
            owner=self.user, balance_type=BalanceEntry.BalanceType.GOLD
        )
        self.assertEqual(
            gold_entries.count(), 2,
            "confirms the duplication mechanism: legacy entry untouched, "
            "new entry created because currency_id didn't match",
        )

    def test_repoint_migration_then_sync_fixes_it_with_no_duplicate(self):
        """The actual fix: run migration 0015's repoint function first
        (as it now does on every fresh deploy/migrate), THEN sync — the
        legacy entry's currency should already be repointed by the time
        sync runs, so it's found, updated in place, and no duplicate is
        created."""
        mod = importlib.import_module("core.migrations.0015_repoint_currency_fks")
        mod.repoint_currency_fks(django_apps, None)

        self.legacy_entry.refresh_from_db()
        self.assertEqual(self.legacy_entry.currency_id, self.user_gold.id)

        _sync_gold_balance_from_assets(self.user)

        gold_entries = BalanceEntry.objects.filter(
            owner=self.user, balance_type=BalanceEntry.BalanceType.GOLD
        )
        self.assertEqual(gold_entries.count(), 1)
        self.assertEqual(gold_entries.first().id, self.legacy_entry.id)
        self.assertEqual(gold_entries.first().amount, Decimal("10.00"))

    def test_running_sync_repeatedly_after_fix_stays_stable(self):
        """Real-world safety net: even without any repoint at all (e.g. a
        record this migration somehow missed), running sync twice in a
        row must never itself create a second duplicate — the second run
        should find and reuse whatever the first run created."""
        _sync_gold_balance_from_assets(self.user)
        first_count = BalanceEntry.objects.filter(
            owner=self.user, balance_type=BalanceEntry.BalanceType.GOLD
        ).count()

        _sync_gold_balance_from_assets(self.user)
        second_count = BalanceEntry.objects.filter(
            owner=self.user, balance_type=BalanceEntry.BalanceType.GOLD
        ).count()

        self.assertEqual(first_count, second_count)
