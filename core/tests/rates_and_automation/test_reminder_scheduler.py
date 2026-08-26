from core.models import AppSettings
from core.models import AssetInsurance
from core.models import FixedAsset
from core.models import RealEstateDetails
from core.models import VehicleDetails
import json
from datetime import date
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from core.models import ReminderLog, ReminderRule
from core.services.shared.reminder_automation_service import ReminderAutomationService
from core.services.shared.scheduler_service import SchedulerService

User = get_user_model()


class ReminderAutomationServiceTest(TestCase):
    def setUp(self):
        self.asset = FixedAsset.objects.create(
            name="Test Vehicle",
            asset_type="Vehicles",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=100000,
            current_market_value=90000,
        )
        self.vehicle = VehicleDetails.objects.create(
            asset=self.asset,
            brand="Toyota",
            plate_number="ABC-123",
            license_expiry_date=date(2026, 7, 7),
        )
        self.insurance = AssetInsurance.objects.create(
            asset=self.asset,
            company="Insurer",
            policy_number="P-1",
            expiry_date=date(2026, 7, 9),
            premium=1000,
        )

    def test_service_generates_insurance_and_vehicle_license_reminders_without_duplicates(self):
        insurance_rule = ReminderRule.objects.create(
            name="Insurance expiry",
            rule_type="insurance_expiry",
            days_before=10,
        )
        vehicle_rule = ReminderRule.objects.create(
            name="Vehicle license expiry",
            rule_type="vehicle_license_expiry",
            days_before=10,
        )

        result = ReminderAutomationService().evaluate(today=date(2026, 7, 4))
        self.assertEqual(result.count, 2)
        self.assertEqual(ReminderLog.objects.count(), 2)

        # Second call on same day: reminders still fire (no suppression), but log stays at 1 per rule
        second = ReminderAutomationService().evaluate(today=date(2026, 7, 4))
        self.assertEqual(second.count, 2)
        self.assertEqual(ReminderLog.objects.filter(rule=insurance_rule).count(), 1)
        self.assertEqual(ReminderLog.objects.filter(rule=vehicle_rule).count(), 1)

    def test_reminder_check_view_uses_service_output(self):
        from unittest.mock import patch
        with patch("django.utils.timezone.localdate") as mock_localdate:
            mock_localdate.return_value = date(2026, 7, 4)
            ReminderRule.objects.create(
                name="Vehicle license expiry",
                rule_type="vehicle_license_expiry",
                days_before=10,
            )

            response = self.client.get("/api/reminders/check/")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["reminders"][0]["rule_type"], "vehicle_license_expiry")

    def test_property_tax_reminder_uses_due_date_settings_and_avoids_duplicates(self):
        real_estate_asset = FixedAsset.objects.create(
            name="Taxed Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=300000,
            current_market_value=500000,
        )
        details = RealEstateDetails.objects.create(
            asset=real_estate_asset,
            country="Egypt",
            city="Cairo",
            governorate="Cairo",
            area_m2=85,
        )
        rule = ReminderRule.objects.create(
            name="Property tax",
            rule_type="property_tax_reminder",
            days_before=10,
        )

        AppSettings.set("property_tax_due_month", "7")
        AppSettings.set("property_tax_due_day", "10")
        AppSettings.set("property_tax_countries", "[\"Egypt\"]")

        first = ReminderAutomationService().evaluate(today=date(2026, 7, 4))
        self.assertEqual(first.count, 1)
        self.assertEqual(first.reminders[0]["rule_type"], "property_tax_reminder")
        self.assertEqual(first.reminders[0]["related_id"], details.id)
        self.assertEqual(first.reminders[0]["days_left"], 6)

        # Second call on same day: reminder still fires, but log entry remains a single record
        second = ReminderAutomationService().evaluate(today=date(2026, 7, 4))
        self.assertEqual(second.count, 1)
        self.assertEqual(
            ReminderLog.objects.filter(
                rule=rule,
                related_model="RealEstateDetails",
                related_id=details.id,
            ).count(),
            1,
        )


class SchedulerAutomationCommandTest(TestCase):
    def test_scheduler_lists_expected_jobs(self):
        jobs = {item["job_id"] for item in SchedulerService().list_jobs()}
        self.assertEqual(
            jobs,
            {
                "reminders",
                "certificate_maturity",
                "certificate_interest",
                "exchange_rates",
                "gold_prices",
                "property_valuation",
            },
        )

    @patch("core.services.shared.scheduler_service.PropertyValuationService.refresh_all")
    @patch("core.services.shared.scheduler_service.GoldValuationService.refresh_latest_prices")
    @patch("core.services.shared.scheduler_service.ExchangeRateService.refresh_latest_rates")
    @patch("core.services.shared.scheduler_service.CertificateInterestService.synchronize")
    @patch("core.services.shared.scheduler_service.CertificateAutomationService.close_matured_certificates")
    @patch("core.services.shared.scheduler_service.ReminderAutomationService.evaluate")
    def test_run_automation_command_executes_registered_jobs(
        self,
        mock_reminders,
        mock_cert_maturity,
        mock_cert_interest,
        mock_rates,
        mock_gold,
        mock_property,
    ):
        class ResultWrapper:
            def __init__(self, payload):
                self.payload = payload

            def to_dict(self):
                return self.payload

        mock_reminders.return_value = ResultWrapper({"count": 1})
        mock_cert_maturity.return_value = ResultWrapper({"closed_certificates": 1})
        mock_cert_interest.return_value = ResultWrapper({"posted_periods": 0})
        mock_rates.return_value = ResultWrapper({"saved": 18})
        mock_gold.return_value = ResultWrapper({"saved": 1})
        mock_property.return_value = ResultWrapper({"updated_assets": 0})

        output = StringIO()
        call_command("run_automation", "--today", "2026-07-04", stdout=output)
        payload = json.loads(output.getvalue())

        self.assertEqual(len(payload), 6)
        self.assertTrue(all(item["success"] for item in payload))
