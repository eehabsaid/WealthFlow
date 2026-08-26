import json
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import BalanceEntry, Bank, Currency, ExchangeRate

User = get_user_model()


class CurrencyExchangeReversalTest(TestCase):
    def setUp(self):
        from django.test import Client
        self.client = Client()
        self.user = User.objects.create_user(username="ce_testuser", password="password")

        # Currencies
        self.egp, _ = Currency.objects.get_or_create(code="EGP", defaults={"name": "Egyptian Pound", "symbol": "EGP"})
        self.usd, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$"})
        self.eur, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro", "symbol": "€"})
        self.sar, _ = Currency.objects.get_or_create(code="SAR", defaults={"name": "Saudi Riyal", "symbol": "﷼"})

        # Exchange rates against base EGP
        ExchangeRate.objects.create(currency_code="USD", currency_name="US Dollar", buy_rate=Decimal("50.000000"))
        ExchangeRate.objects.create(currency_code="EUR", currency_name="Euro", buy_rate=Decimal("55.000000"))
        ExchangeRate.objects.create(currency_code="SAR", currency_name="Saudi Riyal", buy_rate=Decimal("13.333333"))

        # Banks
        self.bank_cib = Bank.objects.create(name="CIB Bank Test")

        # Balance entries
        self.bal_usd = BalanceEntry.objects.create(
            title="USD Cash Test",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.usd,
            amount=Decimal("1000.00")
        )
        self.bal_egp = BalanceEntry.objects.create(
            title="CIB Account Test",
            balance_type=BalanceEntry.BalanceType.BANK,
            bank=self.bank_cib,
            currency=self.egp,
            amount=Decimal("50000.00")
        )
        self.bal_eur = BalanceEntry.objects.create(
            title="EUR Wallet Test",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.eur,
            amount=Decimal("500.00")
        )

    def test_delete_currency_exchange_reversal(self):
        from core.models import CurrencyExchange
        payload = {
            "exchange_date": "2026-08-05",
            "from_balance_id": self.bal_usd.id,
            "to_balance_id": self.bal_egp.id,
            "from_amount": 100.00,
            "exchange_rate": 50.0
        }
        res = self.client.post("/api/currency-exchanges/", json.dumps(payload), content_type="application/json")
        exchange_id = res.json()["id"]

        del_res = self.client.delete(f"/api/currency-exchanges/{exchange_id}/")
        self.assertEqual(del_res.status_code, 200)

        self.bal_usd.refresh_from_db()
        self.bal_egp.refresh_from_db()
        self.assertEqual(self.bal_usd.amount, Decimal("1000.00"))
        self.assertEqual(self.bal_egp.amount, Decimal("50000.00"))

        exchange = CurrencyExchange.objects.get(pk=exchange_id)
        self.assertEqual(exchange.status, CurrencyExchange.Status.REVERSED)
        self.assertIsNotNone(exchange.reversed_at)

    def test_edit_currency_exchange(self):
        payload = {
            "exchange_date": "2026-08-05",
            "from_balance_id": self.bal_usd.id,
            "to_balance_id": self.bal_egp.id,
            "from_amount": 100.00,
            "exchange_rate": 50.0
        }
        res = self.client.post("/api/currency-exchanges/", json.dumps(payload), content_type="application/json")
        exchange_id = res.json()["id"]

        edit_payload = {
            "exchange_date": "2026-08-05",
            "from_balance_id": self.bal_usd.id,
            "to_balance_id": self.bal_egp.id,
            "from_amount": 200.00,
            "exchange_rate": 50.0
        }
        edit_res = self.client.put(f"/api/currency-exchanges/{exchange_id}/", json.dumps(edit_payload), content_type="application/json")
        self.assertEqual(edit_res.status_code, 200)

        self.bal_usd.refresh_from_db()
        self.bal_egp.refresh_from_db()
        self.assertEqual(self.bal_usd.amount, Decimal("800.00"))
        self.assertEqual(self.bal_egp.amount, Decimal("60000.00"))

    def test_insufficient_balance_validation(self):
        payload = {
            "exchange_date": "2026-08-05",
            "from_balance_id": self.bal_usd.id,
            "to_balance_id": self.bal_egp.id,
            "from_amount": 5000.00,
            "exchange_rate": 50.0
        }
        res = self.client.post("/api/currency-exchanges/", json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("insufficient_balance_error", res.json()["error"])

    def test_same_balance_validation(self):
        payload = {
            "exchange_date": "2026-08-05",
            "from_balance_id": self.bal_usd.id,
            "to_balance_id": self.bal_usd.id,
            "from_amount": 50.00
        }
        res = self.client.post("/api/currency-exchanges/", json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("same_balance_error", res.json()["error"])
