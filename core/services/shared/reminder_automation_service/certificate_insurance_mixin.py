from __future__ import annotations

from datetime import timedelta

from core.models import AssetInsurance, BankCertificate, ReminderLog


class CertificateInsuranceMixin:
    """Evaluates bank-certificate maturity and asset-insurance expiry reminder rules."""

    def _evaluate_certificate_maturity(self, rule, today):
        target = today + timedelta(days=rule.days_before)
        reminders = []

        for cert in BankCertificate.objects.filter(
            expiry_date__gte=today,
            expiry_date__lte=target,
            status__iexact="active",
        ):
            days_left = (cert.expiry_date - today).days
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
