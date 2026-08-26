from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import (
    AssetMortgage,
    AssetRental,
    BalanceEntry,
    Currency,
    FixedAsset,
)

User = get_user_model()


class RentalIncomeSynchronizationTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.asset = FixedAsset.objects.create(
            name="Rental Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=500000,
            current_market_value=600000,
        )

    def test_rental_income_updates_balance_forecast_and_reports_income(self):
        rental = AssetRental.objects.create(
            asset=self.asset,
            monthly_rent=1000,
            occupancy_rate=80,
            tenant_name="Tenant A",
        )

        self.assertFalse(
            BalanceEntry.objects.filter(notes__startswith="wealthflow:rental-income:asset:").exists()
        )

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        balance_payload = balance_response.json()
        self.assertEqual(balance_payload["summary"]["grand_total"], 800.0)

        forecast_response = self.client.get("/api/certificate-forecast/")
        self.assertEqual(forecast_response.status_code, 200)
        forecast_payload = forecast_response.json()
        self.assertEqual(forecast_payload["monthly_rental_income"], 800.0)

        report_response = self.client.get("/api/expenses/summary/?year=2026&month=7")
        self.assertEqual(report_response.status_code, 200)
        report_payload = report_response.json()["income_summary"]
        self.assertEqual(report_payload["total_rental_income"], 800.0)
        self.assertEqual(report_payload["total_income"], 800.0)

        rental.delete()
        self.assertFalse(
            BalanceEntry.objects.filter(notes__startswith="wealthflow:rental-income:asset:").exists()
        )

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.json()["summary"]["grand_total"], 0.0)


class MortgageSynchronizationTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.asset = FixedAsset.objects.create(
            name="Mortgage Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=500000,
            current_market_value=600000,
        )

    def test_mortgage_updates_balance_and_clears_on_delete(self):
        mortgage = AssetMortgage.objects.create(
            asset=self.asset,
            loan_amount=300000,
            remaining_balance=240000,
            monthly_installment=5000,
            interest_rate=8.5,
            start_date=date(2026, 1, 1),
        )

        self.assertFalse(
            BalanceEntry.objects.filter(notes__startswith="wealthflow:mortgage-liability:asset:").exists()
        )

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.json()["summary"]["net_worth"], 360000.0)

        mortgage.remaining_balance = 200000
        mortgage.save()

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.json()["summary"]["net_worth"], 400000.0)

        mortgage.delete()
        self.assertFalse(
            BalanceEntry.objects.filter(notes__startswith="wealthflow:mortgage-liability:asset:").exists()
        )

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.json()["summary"]["net_worth"], 600000.0)
