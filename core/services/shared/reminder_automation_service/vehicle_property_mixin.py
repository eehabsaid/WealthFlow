from __future__ import annotations

import json
from calendar import monthrange
from datetime import date, timedelta

from core.models import AppSettings, FixedAsset, ReminderLog, VehicleDetails


class VehiclePropertyMixin:
    """Evaluates vehicle license expiry and property tax reminder rules."""

    def _evaluate_vehicle_license_expiry(self, rule, today):
        reminders = []
        target = today + timedelta(days=rule.days_before)
        for vehicle in VehicleDetails.objects.select_related("asset").filter(
            license_expiry_date__gte=today,
            license_expiry_date__lte=target,
        ):
            days_left = (vehicle.license_expiry_date - today).days
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
