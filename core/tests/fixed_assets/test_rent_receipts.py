"""'Rent received': the real deposit settles the month's virtual rental income, so rent counts once."""

import json
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.models import AssetRental, Bank, BalanceEntry, Currency, FixedAsset, RentReceipt
from core.services.fixed_assets.rent_receipt_service import RentReceiptError, delete_receipt, record_receipt

User = get_user_model()


class RentReceiptTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="rr_user", password="pass12345")
        self.client.force_login(self.user)
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.asset = FixedAsset.objects.create(
            owner=self.user, name="Flat", asset_type="Real Estate", status="Owned",
            purchase_date=date(2026, 1, 1), purchase_price=500000, current_market_value=600000,
        )
        self.rental = AssetRental.objects.create(asset=self.asset, monthly_rent=1000, occupancy_rate=80)

    def total(self):
        return self.client.get("/api/balance/").json()["summary"]["grand_total"]

    def post(self, **body):
        return self.client.post(f"/api/fixed-assets/{self.asset.id}/rent-receipts/", data=json.dumps(body), content_type="application/json")

    def test_rent_counts_once_after_it_is_received(self):
        self.assertEqual(self.total(), 800.0)  # virtual month of rent
        receipt = record_receipt(self.user, self.rental)  # default amount = rent x occupancy
        self.assertEqual(float(receipt.amount), 800.0)
        self.assertEqual(self.total(), 800.0)  # real deposit replaces the virtual line: NOT 1600
        self.assertEqual(float(BalanceEntry.objects.get(owner=self.user).amount), 800.0)

    def test_actual_amount_can_differ_and_delete_restores_the_virtual_month(self):
        receipt = record_receipt(self.user, self.rental, amount="750.50")
        self.assertEqual(self.total(), 750.5)
        delete_receipt(receipt)
        self.assertEqual(self.total(), 800.0)
        self.assertEqual(float(BalanceEntry.objects.get(owner=self.user).amount), 0.0)
        self.assertFalse(RentReceipt.objects.exists())

    def test_only_the_current_month_is_settled_by_a_current_month_receipt(self):
        record_receipt(self.user, self.rental, period="2020-01")  # an old month
        self.assertEqual(self.total(), 1600.0)  # deposit 800 + this month's virtual 800

    def test_one_receipt_per_month_and_amount_must_be_positive(self):
        record_receipt(self.user, self.rental)
        with self.assertRaises(RentReceiptError) as dup:
            record_receipt(self.user, self.rental)
        self.assertEqual(dup.exception.status, 409)
        AssetRental.objects.filter(pk=self.rental.pk).update(monthly_rent=0)
        self.rental.refresh_from_db()
        with self.assertRaises(RentReceiptError):
            record_receipt(self.user, self.rental, period="2020-02")
        with self.assertRaises(RentReceiptError):
            record_receipt(self.user, self.rental, period="2020-02", amount="abc")
        with self.assertRaises(RentReceiptError):
            record_receipt(self.user, self.rental, period="nope", amount="5")

    def test_bank_rental_credits_that_bank_account(self):
        bank = Bank.objects.create(owner=self.user, name="NBE")
        AssetRental.objects.filter(pk=self.rental.pk).update(receive_method="Bank", bank=bank)
        self.rental.refresh_from_db()
        receipt = record_receipt(self.user, self.rental)
        self.assertEqual(receipt.bank_id, bank.id)
        entry = BalanceEntry.objects.get(owner=self.user)
        self.assertEqual((entry.bank_id, entry.balance_type, float(entry.amount)), (bank.id, "bank", 800.0))

    def test_api_create_list_delete_and_isolation(self):
        res = self.post(amount="800")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.post(amount="800").status_code, 409)
        listing = self.client.get(f"/api/fixed-assets/{self.asset.id}/rent-receipts/").json()
        self.assertTrue(listing["current_month_settled"])
        self.assertEqual(listing["current_period"], timezone.localdate().strftime("%Y-%m"))
        other = User.objects.create_user(username="rr_other", password="pass12345")
        self.client.force_login(other)
        self.assertEqual(self.client.get(f"/api/fixed-assets/{self.asset.id}/rent-receipts/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/rent-receipts/{res.json()['id']}/").status_code, 404)
        self.client.force_login(self.user)
        self.assertEqual(self.client.delete(f"/api/rent-receipts/{res.json()['id']}/").status_code, 200)
        self.assertEqual(self.total(), 800.0)

    def test_api_requires_login_and_validates_input(self):
        self.assertEqual(self.post(period="bad", amount="5").status_code, 400)
        self.assertEqual(self.post(amount="-1").status_code, 400)
        self.client.logout()
        self.assertIn(self.post(amount="5").status_code, (401, 403))
