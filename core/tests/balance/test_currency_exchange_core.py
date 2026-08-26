import json
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import BalanceEntry, Bank, Currency, ExchangeRate

User = get_user_model()


class CurrencyExchangeCoreTest(TestCase):
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

    def test_currency_conversion_service(self):
        from core.services.shared.currency_conversion_service import CurrencyConversionService
        rate = CurrencyConversionService.calculate_exchange_rate("USD", "EGP")
        self.assertEqual(rate, Decimal("50.000000"))
        applied_rate, to_amt = CurrencyConversionService.convert_amount(Decimal("100.00"), "USD", "EGP")
        self.assertEqual(to_amt, Decimal("5000.00"))

        rate_egp_usd = CurrencyConversionService.calculate_exchange_rate("EGP", "USD")
        self.assertEqual(rate_egp_usd, Decimal("0.020000"))
        _, to_amt_usd = CurrencyConversionService.convert_amount(Decimal("5000.00"), "EGP", "USD")
        self.assertEqual(to_amt_usd, Decimal("100.00"))

        rate_usd_eur = CurrencyConversionService.calculate_exchange_rate("USD", "EUR")
        self.assertEqual(rate_usd_eur, Decimal("0.909091"))

    def test_calculate_backend_endpoint(self):
        payload = {
            "from_balance_id": self.bal_usd.id,
            "to_balance_id": self.bal_egp.id,
            "from_amount": 200.00
        }
        res = self.client.post("/api/currency-exchanges/calculate/", json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["exchange_rate"], 50.0)
        self.assertEqual(data["to_amount"], 10000.0)
        self.assertEqual(data["available_balance"], 1000.0)

    def test_create_currency_exchange_and_balance_update(self):
        from core.models import CurrencyExchange
        payload = {
            "exchange_date": "2026-08-05",
            "from_balance_id": self.bal_usd.id,
            "to_balance_id": self.bal_egp.id,
            "from_amount": 100.00,
            "exchange_rate": 50.0,
            "notes": "Exchange test USD to EGP"
        }
        res = self.client.post("/api/currency-exchanges/", json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 201)

        self.bal_usd.refresh_from_db()
        self.bal_egp.refresh_from_db()
        self.assertEqual(self.bal_usd.amount, Decimal("900.00"))
        self.assertEqual(self.bal_egp.amount, Decimal("55000.00"))

        exchange_id = res.json()["id"]
        exchange = CurrencyExchange.objects.get(pk=exchange_id)
        self.assertEqual(exchange.status, CurrencyExchange.Status.ACTIVE)

    def test_filter_by_currency(self):
        """GET /api/currency-exchanges/?currency=USD must return 200 and only
        exchanges where from_currency or to_currency matches USD."""
        payload = {
            "exchange_date": "2026-08-05",
            "from_balance_id": self.bal_usd.id,
            "to_balance_id": self.bal_egp.id,
            "from_amount": 100.00,
            "exchange_rate": 50.0,
            "notes": "USD-EGP filter test"
        }
        self.client.post("/api/currency-exchanges/", json.dumps(payload), content_type="application/json")

        res = self.client.get("/api/currency-exchanges/?currency=USD")
        self.assertEqual(res.status_code, 200)
        exchanges = res.json()["exchanges"]
        self.assertGreaterEqual(len(exchanges), 1)
        for ex in exchanges:
            self.assertTrue(
                ex["from_currency_code"] == "USD" or ex["to_currency_code"] == "USD",
                f"Exchange {ex['id']} does not involve USD"
            )

        # Filter by a currency not used — should return empty
        res_sar = self.client.get("/api/currency-exchanges/?currency=SAR")
        self.assertEqual(res_sar.status_code, 200)
        self.assertEqual(len(res_sar.json()["exchanges"]), 0)

    def test_filter_by_balance_id(self):
        """GET /api/currency-exchanges/?balance_id=<id> must return 200 and only
        exchanges where from_balance or to_balance matches the given id."""
        payload = {
            "exchange_date": "2026-08-05",
            "from_balance_id": self.bal_usd.id,
            "to_balance_id": self.bal_egp.id,
            "from_amount": 100.00,
            "exchange_rate": 50.0,
        }
        self.client.post("/api/currency-exchanges/", json.dumps(payload), content_type="application/json")

        res = self.client.get(f"/api/currency-exchanges/?balance_id={self.bal_usd.id}")
        self.assertEqual(res.status_code, 200)
        exchanges = res.json()["exchanges"]
        self.assertGreaterEqual(len(exchanges), 1)
        for ex in exchanges:
            self.assertTrue(
                ex["from_balance_id"] == self.bal_usd.id or ex["to_balance_id"] == self.bal_usd.id,
                f"Exchange {ex['id']} does not involve balance {self.bal_usd.id}"
            )

        # Filter by uninvolved balance — should return empty
        res_eur = self.client.get(f"/api/currency-exchanges/?balance_id={self.bal_eur.id}")
        self.assertEqual(res_eur.status_code, 200)
        self.assertEqual(len(res_eur.json()["exchanges"]), 0)

    def test_filter_by_user(self):
        """GET /api/currency-exchanges/?user=<username> must return 200 and
        filter exchanges by user username or id. The critical assertion is
        that this returns HTTP 200, NOT 500 (the original NameError bug)."""
        payload = {
            "exchange_date": "2026-08-05",
            "from_balance_id": self.bal_usd.id,
            "to_balance_id": self.bal_egp.id,
            "from_amount": 100.00,
            "exchange_rate": 50.0,
        }
        self.client.post("/api/currency-exchanges/", json.dumps(payload), content_type="application/json")

        # Filter by username — should return 200 with results
        res = self.client.get("/api/currency-exchanges/?user=ce_testuser")
        self.assertEqual(res.status_code, 200)
        exchanges = res.json()["exchanges"]
        self.assertIsInstance(exchanges, list)

        # Filter by numeric user ID that doesn't exist — should return 200 with empty list
        res_none = self.client.get("/api/currency-exchanges/?user=99999")
        self.assertEqual(res_none.status_code, 200)
        self.assertEqual(len(res_none.json()["exchanges"]), 0)
