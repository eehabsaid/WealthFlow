"""RentReceipt (rent received) survives backup -> delete -> restore with its amount, month, bank and rental link."""

import os
import shutil
import tempfile
import zipfile
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from core.models import AssetRental, Bank, Currency, FixedAsset, RentReceipt


class RentReceiptBackupTests(TestCase):
    def test_round_trip(self):
        user = get_user_model().objects.create_user(username="bk_rent_user", password="Pw123456!")
        egp = Currency.objects.get_or_create(owner=user, code="EGP", defaults={"symbol": "E", "name": "Egyptian Pound"})[0]
        bank = Bank.objects.create(owner=user, name="NBE")
        asset = FixedAsset.objects.create(owner=user, name="Flat", asset_type="Real Estate", status="Owned",
                                          purchase_date=date(2026, 1, 1), purchase_price=1, current_market_value=1)
        rental = AssetRental.objects.create(asset=asset, monthly_rent=1000, occupancy_rate=100)
        RentReceipt.objects.create(owner=user, rental=rental, period_start=date(2026, 9, 1), received_date=date(2026, 9, 3),
                                   bank=bank, currency=egp, amount=Decimal("950.50"), notes="September")
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "r.wfbackup")
            call_command("backup_data", output=tmp, filename="r.wfbackup", no_compress=True)
            with zipfile.ZipFile(path) as zf:
                self.assertTrue(any(n.endswith("_rentreceipt.json") for n in zf.namelist()), zf.namelist())
            RentReceipt.objects.all().delete()
            call_command("restore_data", path)
            r = RentReceipt.objects.get(owner=user)
            self.assertEqual((r.period_start, r.received_date, r.amount, r.notes), (date(2026, 9, 1), date(2026, 9, 3), Decimal("950.50"), "September"))
            self.assertEqual((r.rental_id, r.bank_id, r.currency_id), (rental.id, bank.id, egp.id))
        finally:
            shutil.rmtree(tmp)
