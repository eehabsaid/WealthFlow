from datetime import date

from django.db import migrations


def _add_months(base_date, months):
    month_index = base_date.month - 1 + months
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(
        base_date.day,
        [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1],
    )
    return date(year, month, day)


def _normalize_frequency(value):
    text = str(value or "").strip().lower()
    if text in {"semi_annually", "semi-annually", "semi annually", "semiannual", "semi-annual", "semi yearly", "semi-yearly"}:
        return "semi-yearly"
    if text in {"annually", "annual", "yearly"}:
        return "yearly"
    if text in {"monthly", "quarterly", "at_maturity"}:
        return text
    return ""


def _scheduled_dates(issue_date, expiry_date, frequency):
    if not issue_date or not expiry_date or expiry_date < issue_date:
        return []

    freq = _normalize_frequency(frequency)
    if not freq:
        return []

    if freq == "at_maturity":
        return [expiry_date]

    months_step_map = {
        "monthly": 1,
        "quarterly": 3,
        "semi-yearly": 6,
        "yearly": 12,
    }
    step = months_step_map.get(freq)
    if not step:
        return []

    out = []
    i = 1
    next_date = _add_months(issue_date, step * i)
    while next_date <= expiry_date:
        out.append(next_date)
        i += 1
        next_date = _add_months(issue_date, step * i)
    return out


def backfill_closed_certificate_history(apps, schema_editor):
    BankCertificate = apps.get_model("core", "BankCertificate")
    BankCertificateInterestHistory = apps.get_model("core", "BankCertificateInterestHistory")

    certificates = BankCertificate.objects.all()
    for cert in certificates:
        status = str(getattr(cert, "status", "") or "").strip().lower()
        if status == "active":
            continue

        due_dates = _scheduled_dates(cert.issue_date, cert.expiry_date, cert.frequency)
        for due_date in due_dates:
            BankCertificateInterestHistory.objects.get_or_create(
                certificate_id=cert.id,
                posting_date=due_date,
                defaults={
                    "posting_period": f"{cert.frequency or 'Period'}:{due_date.isoformat()}",
                    "interest_amount": cert.interest_value or 0,
                    "bank_id": cert.bank_id,
                    "currency_id": cert.currency_id,
                },
            )


def noop_reverse(apps, schema_editor):
    # Keep historical data intact on reverse to avoid deleting user/audit-visible rows.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_bankcertificate_interest_sync"),
    ]

    operations = [
        migrations.RunPython(backfill_closed_certificate_history, noop_reverse),
    ]
