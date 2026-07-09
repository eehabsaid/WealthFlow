from __future__ import annotations

import json
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from core.models import (
    AppSettings,
    AssetInsurance,
    BankCertificate,
    FixedAsset,
    ReminderLog,
    ReminderRule,
    SalaryEntry,
    VehicleDetails,
)


@dataclass
class ReminderAutomationResult:
    reminders: list

    @property
    def count(self) -> int:
        return len(self.reminders)

    def to_dict(self):
        return {"reminders": self.reminders, "count": self.count}


class ReminderAutomationService:
    """Evaluates active reminder rules and event-based reminders in one place."""

    def evaluate(self, today=None):
        current_date = today or timezone.localdate()
        reminders = []

        with transaction.atomic():
            for rule in ReminderRule.objects.filter(is_active=True):
                reminders.extend(self._evaluate_rule(rule, current_date))

        return ReminderAutomationResult(reminders=reminders)

    def _evaluate_rule(self, rule, today):
        rule_type = str(rule.rule_type or "").strip().lower()
        if rule_type == "cert_maturity":
            return self._evaluate_certificate_maturity(rule, today)
        if rule_type == "insurance_expiry":
            return self._evaluate_insurance_expiry(rule, today)
        if rule_type == "vehicle_license_expiry":
            return self._evaluate_vehicle_license_expiry(rule, today)
        if rule_type == "property_tax_reminder":
            return self._evaluate_property_tax_reminder(rule, today)
        if rule_type == "salary_unpaid":
            return self._evaluate_salary_unpaid(rule, today)
        if rule_type == "salary_day":
            return self._evaluate_salary_day(rule, today)
        if rule_type == "custom":
            return self._evaluate_custom(rule, today)
        return []

    def _evaluate_certificate_maturity(self, rule, today):
        target = today + timedelta(days=rule.days_before)
        reminders = []

        for cert in BankCertificate.objects.filter(
            expiry_date__gte=today,
            expiry_date__lte=target,
        ):
            days_left = (cert.expiry_date - today).days
            already = ReminderLog.objects.filter(
                rule=rule,
                related_model="BankCertificate",
                related_id=cert.id,
                fired_on=today,
            ).exists()
            if already:
                continue

            bank_name = cert.bank.name if cert.bank else "Unknown"
            message = (
                f"Certificate at {bank_name} of {float(cert.amount):,.2f} expires in {days_left} day(s) on {cert.expiry_date}."
            )
            ReminderLog.objects.get_or_create(
                rule=rule,
                related_model="BankCertificate",
                related_id=cert.id,
                fired_on=today,
                defaults={"message": message},
            )
            reminders.append(
                {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "rule_type": rule.rule_type,
                    "message": message,
                    "related_id": cert.id,
                    "link": "bank-certificates",
                    "days_left": days_left,
                }
            )

        return reminders

    def _evaluate_insurance_expiry(self, rule, today):
        reminders = []
        target = today + timedelta(days=rule.days_before)
        for insurance in AssetInsurance.objects.select_related("asset").filter(
            expiry_date__gte=today,
            expiry_date__lte=target,
        ):
            days_left = (insurance.expiry_date - today).days
            already = ReminderLog.objects.filter(
                rule=rule,
                related_model="AssetInsurance",
                related_id=insurance.id,
                fired_on=today,
            ).exists()
            if already:
                continue

            asset_name = insurance.asset.name if insurance.asset else "Unknown"
            message = (
                f"Insurance for {asset_name} expires in {days_left} day(s) on {insurance.expiry_date}."
            )
            ReminderLog.objects.get_or_create(
                rule=rule,
                related_model="AssetInsurance",
                related_id=insurance.id,
                fired_on=today,
                defaults={"message": message},
            )
            reminders.append(
                {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "rule_type": rule.rule_type,
                    "message": message,
                    "related_id": insurance.id,
                    "link": "fixed-assets",
                    "days_left": days_left,
                }
            )
        return reminders

    def _evaluate_vehicle_license_expiry(self, rule, today):
        reminders = []
        target = today + timedelta(days=rule.days_before)
        for vehicle in VehicleDetails.objects.select_related("asset").filter(
            license_expiry_date__gte=today,
            license_expiry_date__lte=target,
        ):
            days_left = (vehicle.license_expiry_date - today).days
            already = ReminderLog.objects.filter(
                rule=rule,
                related_model="VehicleDetails",
                related_id=vehicle.id,
                fired_on=today,
            ).exists()
            if already:
                continue

            asset_name = vehicle.asset.name if vehicle.asset else "Unknown"
            plate_number = vehicle.plate_number or "-"
            message = (
                f"Vehicle license for {asset_name} ({plate_number}) expires in {days_left} day(s) on {vehicle.license_expiry_date}."
            )
            ReminderLog.objects.get_or_create(
                rule=rule,
                related_model="VehicleDetails",
                related_id=vehicle.id,
                fired_on=today,
                defaults={"message": message},
            )
            reminders.append(
                {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "rule_type": rule.rule_type,
                    "message": message,
                    "related_id": vehicle.id,
                    "link": "fixed-assets",
                    "days_left": days_left,
                }
            )

        return reminders

    def _evaluate_property_tax_reminder(self, rule, today):
        reminders = []
        target = today + timedelta(days=rule.days_before)
        due_date = self._property_tax_due_date(today.year)

        if due_date < today or due_date > target:
            return reminders

        allowed_countries = self._property_tax_allowed_countries()
        assets = FixedAsset.objects.select_related("real_estate").filter(
            asset_type="Real Estate",
            status="Owned",
        )

        for asset in assets:
            details = getattr(asset, "real_estate", None)
            if not details:
                continue

            country = str(details.country or "").strip()
            if allowed_countries and country.lower() not in allowed_countries:
                continue

            already = ReminderLog.objects.filter(
                rule=rule,
                related_model="RealEstateDetails",
                related_id=details.id,
                fired_on=today,
            ).exists()
            if already:
                continue

            location = ", ".join(
                value
                for value in [
                    str(details.city or "").strip(),
                    str(details.governorate or "").strip(),
                    country,
                ]
                if value
            ) or "Unknown location"

            days_left = (due_date - today).days
            message = (
                f"Property tax reminder for {asset.name} ({location}): due in {days_left} day(s) on {due_date}."
            )
            ReminderLog.objects.get_or_create(
                rule=rule,
                related_model="RealEstateDetails",
                related_id=details.id,
                fired_on=today,
                defaults={"message": message},
            )
            reminders.append(
                {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "rule_type": rule.rule_type,
                    "message": message,
                    "related_id": details.id,
                    "link": "fixed-assets",
                    "days_left": days_left,
                }
            )

        return reminders

    def _evaluate_salary_unpaid(self, rule, today):
        trigger_day = self._salary_trigger_day(rule, today)
        if today.day < trigger_day:
            return []

        unpaid = SalaryEntry.objects.filter(year=today.year, month=today.month, paid=0).exists()
        if not unpaid:
            return []

        already = ReminderLog.objects.filter(
            rule=rule,
            related_model="SalaryEntry",
            related_id=0,
            fired_on=today,
        ).exists()
        if already:
            return []

        message = rule.salary_message or "This month has unpaid salary entries."
        ReminderLog.objects.get_or_create(
            rule=rule,
            related_model="SalaryEntry",
            related_id=0,
            fired_on=today,
            defaults={"message": message},
        )
        return [
            {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "rule_type": rule.rule_type,
                "message": message,
                "link": "salary",
            }
        ]

    def _evaluate_salary_day(self, rule, today):
        trigger_day = self._salary_trigger_day(rule, today)
        if today.day < trigger_day:
            return []

        already = ReminderLog.objects.filter(
            rule=rule,
            related_model="SalaryDay",
            related_id=today.month,
            fired_on=today,
        ).exists()
        if already:
            return []

        message = rule.salary_message or f'Salary day reminder for {today.strftime("%B %Y")}. '
        ReminderLog.objects.get_or_create(
            rule=rule,
            related_model="SalaryDay",
            related_id=today.month,
            fired_on=today,
            defaults={"message": message},
        )
        return [
            {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "rule_type": rule.rule_type,
                "message": message,
                "link": "salary",
            }
        ]

    def _evaluate_custom(self, rule, today):
        trigger_day = self._salary_trigger_day(rule, today)
        if today.day < trigger_day:
            return []

        already = ReminderLog.objects.filter(
            rule=rule,
            related_model="Custom",
            related_id=today.month,
            fired_on=today,
        ).exists()
        if already:
            return []

        message = rule.salary_message or rule.name
        ReminderLog.objects.get_or_create(
            rule=rule,
            related_model="Custom",
            related_id=today.month,
            fired_on=today,
            defaults={"message": message},
        )
        return [
            {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "rule_type": rule.rule_type,
                "message": message,
                "link": "",
            }
        ]

    def _salary_trigger_day(self, rule, today):
        import calendar as cal

        last_day = cal.monthrange(today.year, today.month)[1]
        trigger = str(rule.salary_trigger or "").strip().lower()
        if trigger == "day_of_month":
            return min(int(rule.salary_day or 1), last_day)
        if trigger == "days_before_eom":
            return max(1, last_day - int(rule.salary_day or 1))
        if trigger == "days_after_som":
            return min(int(rule.salary_day or 1) + 1, last_day)
        return min(int(rule.salary_day or 1), last_day)

    def _property_tax_due_date(self, year):
        month = self._clamp_int(
            AppSettings.get("property_tax_due_month", "3"),
            default=3,
            min_value=1,
            max_value=12,
        )
        max_day = monthrange(year, month)[1]
        day = self._clamp_int(
            AppSettings.get("property_tax_due_day", "31"),
            default=31,
            min_value=1,
            max_value=max_day,
        )
        return date(year, month, day)

    def _property_tax_allowed_countries(self):
        raw = str(AppSettings.get("property_tax_countries", "") or "").strip()
        if not raw:
            return set()

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return {str(item).strip().lower() for item in parsed if str(item).strip()}
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

        return {item.strip().lower() for item in raw.split(",") if item.strip()}

    def _clamp_int(self, raw_value, default, min_value, max_value):
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            value = default
        return max(min_value, min(max_value, value))
