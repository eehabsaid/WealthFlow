import json
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class PerDiemServiceTest(TestCase):
    def setUp(self):
        from core.models import Currency, Bank, Company, ExchangeRate
        from decimal import Decimal
        self.currency_usd, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$", "flag": "🇺🇸", "order": 1})
        self.currency_egp, _ = Currency.objects.get_or_create(code="EGP", defaults={"name": "Egyptian Pound", "symbol": "EGP", "flag": "🇪🇬", "order": 2})
        
        self.bank, _ = Bank.objects.get_or_create(name="Chase Bank", defaults={"account_number": "1234", "card_id": "5678", "swift_code": "CHAS"})
        self.company, _ = Company.objects.get_or_create(
            name="Giza Systems",
            defaults={
                "display_name": "Giza Systems Disp",
                "is_active": True,
            }
        )
        
        # Add exchange rate for USD
        ExchangeRate.objects.create(
            currency_code="USD",
            currency_name="US Dollar",
            buy_rate=Decimal("50.000000"),
            sell_rate=Decimal("50.500000"),
            mid_rate=Decimal("50.250000"),
        )

    def test_create_per_diem_converts_amount_and_updates_balance(self):
        from core.models import PerDiem, BalanceEntry
        post_data = {
            "company_id": self.company.id,
            "year": 2026,
            "date": "2026-07-08",
            "currency_id": self.currency_usd.id,
            "amount": 100.0,
            "bank_id": self.bank.id,
            "notes": "Testing creation",
        }
        
        response = self.client.post("/api/per-diems/", data=json.dumps(post_data), content_type="application/json")
        if response.status_code != 201:
            print("ERROR RESP:", response.content)
        self.assertEqual(response.status_code, 201)
        
        # Verify db record
        pd = PerDiem.objects.get(id=response.json()["id"])
        self.assertEqual(pd.amount, Decimal("100.00"))
        self.assertEqual(pd.amount_egp, Decimal("5000.00")) # 100 * 50
        
        # Verify balance entry
        bal = BalanceEntry.objects.get(bank=self.bank, currency=self.currency_usd, balance_type="cash")
        self.assertEqual(bal.amount, Decimal("100.00"))

    def test_update_per_diem_adjusts_or_reverses_balance(self):
        from core.models import PerDiem, BalanceEntry
        
        # Create first
        post_data = {
            "company_id": self.company.id,
            "year": 2026,
            "date": "2026-07-08",
            "currency_id": self.currency_usd.id,
            "amount": 100.0,
            "bank_id": self.bank.id,
            "notes": "Testing creation",
        }
        response = self.client.post("/api/per-diems/", data=json.dumps(post_data), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        pd_id = response.json()["id"]
        
        # Update bank to Cash (None) and amount to 150
        put_data = {
            "amount": 150.0,
            "bank_id": None,
        }
        response = self.client.put(f"/api/per-diems/{pd_id}/", data=json.dumps(put_data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        
        # Check database updated
        pd = PerDiem.objects.get(id=pd_id)
        self.assertEqual(pd.amount, Decimal("150.00"))
        self.assertEqual(pd.amount_egp, Decimal("7500.00"))
        self.assertIsNone(pd.bank)
        
        # Verify old balance entry reversed (Chase / USD amount should be 0)
        bal_old = BalanceEntry.objects.get(bank=self.bank, currency=self.currency_usd, balance_type="cash")
        self.assertEqual(bal_old.amount, Decimal("0.00"))
        
        # Verify new balance entry created (Cash (None) / USD amount should be 150)
        bal_new = BalanceEntry.objects.get(bank=None, currency=self.currency_usd, balance_type="cash")
        self.assertEqual(bal_new.amount, Decimal("150.00"))

    def test_delete_per_diem_reverses_balance_and_deletes_record(self):
        from core.models import PerDiem, BalanceEntry
        
        # Create first
        post_data = {
            "company_id": self.company.id,
            "year": 2026,
            "date": "2026-07-08",
            "currency_id": self.currency_usd.id,
            "amount": 100.0,
            "bank_id": self.bank.id,
        }
        response = self.client.post("/api/per-diems/", data=json.dumps(post_data), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        pd_id = response.json()["id"]
        
        # Verify balance entry exists with 100
        bal = BalanceEntry.objects.get(bank=self.bank, currency=self.currency_usd, balance_type="cash")
        self.assertEqual(bal.amount, Decimal("100.00"))
        
        # Delete
        response = self.client.delete(f"/api/per-diems/{pd_id}/")
        self.assertEqual(response.status_code, 200)
        
        # Verify deleted from db
        self.assertFalse(PerDiem.objects.filter(id=pd_id).exists())
        
        # Verify balance entry reversed (0.00)
        bal.refresh_from_db()
        self.assertEqual(bal.amount, Decimal("0.00"))

    def test_get_single_per_diem(self):
        # Create first
        post_data = {
            "company_id": self.company.id,
            "year": 2026,
            "date": "2026-07-08",
            "currency_id": self.currency_usd.id,
            "amount": 120.0,
            "bank_id": self.bank.id,
        }
        response = self.client.post("/api/per-diems/", data=json.dumps(post_data), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        pd_id = response.json()["id"]

        # Fetch detail
        response = self.client.get(f"/api/per-diems/{pd_id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["amount"], 120.0)
        self.assertEqual(data["currency_code"], "USD")
    def test_currency_filtering_only_shows_balance_currencies(self):
        from core.models import BalanceEntry
        from decimal import Decimal
        
        # Initially no balance entries, so currencies endpoint should return empty list
        response = self.client.get("/api/per-diems/currencies/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["currencies"]), 0)
        
        # Create a BalanceEntry for USD
        BalanceEntry.objects.create(
            title="My Balance",
            balance_type="cash",
            bank=self.bank,
            currency=self.currency_usd,
            amount=Decimal("1000.00")
        )
        
        # Now USD should show up
        response = self.client.get("/api/per-diems/currencies/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["currencies"]), 1)
        self.assertEqual(response.json()["currencies"][0]["code"], "USD")
