"""
seed_data.py  –  Django management command
=============================================
Usage
-----
    python manage.py seed_data

Seeds the database with initial data ported from the original Excel
workbook: companies, salary history, currencies, banks, balance entries,
and default app settings.

Note on file layout: the static seed constants (COMPANIES, SALARY_DATA,
CURRENCIES, BANKS, BALANCE_DATA, SETTINGS_DATA) live in
core.services.seed_data (not in this file) to keep this module under 200
lines. They can't be split into a sibling package under
management/commands/ instead, because Django's management-command
auto-discovery (pkgutil.iter_modules with `not is_pkg`) only recognizes
flat modules there, not packages.
"""

from django.core.management.base import BaseCommand
from core.models import Company, SalaryEntry, Bank, BalanceEntry, AppSettings, Currency

from core.services.seed_data import (
    COMPANIES,
    SALARY_DATA,
    CURRENCIES,
    BANKS,
    BALANCE_DATA,
    SETTINGS_DATA,
)


class Command(BaseCommand):
    help = "Seed the database with initial data from the Excel workbook"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding companies...")
        for c in COMPANIES:
            Company.objects.get_or_create(name=c["name"], defaults=c)

        self.stdout.write("Seeding salary entries...")
        for company_name, entries in SALARY_DATA.items():
            company = Company.objects.get(name=company_name)
            for entry in entries:
                year, month, expected, paid = entry[0], entry[1], entry[2], entry[3]
                bonus = entry[4] if len(entry) > 4 else 0
                SalaryEntry.objects.get_or_create(
                    company=company, year=year, month=month,
                    defaults={"expected": expected, "paid": paid, "bonus": bonus},
                )

        self.stdout.write("Seeding banks...")
        bank_map = {}
        for b in BANKS:
            bank, _ = Bank.objects.get_or_create(name=b["name"], defaults=b)
            bank_map[b["name"]] = bank

        self.stdout.write("Seeding currencies...")
        currency_map = {}
        for c in CURRENCIES:
            obj, _ = Currency.objects.get_or_create(code=c["code"], defaults=c)
            currency_map[c["code"]] = obj

        self.stdout.write("Seeding balance entries...")
        for b in BALANCE_DATA:
            bank = bank_map.get(b["bank"]) if b["bank"] else None
            currency_obj = currency_map.get(b["currency"])
            BalanceEntry.objects.get_or_create(
                title=b["title"], currency=currency_obj,
                defaults={"bank": bank, "amount": b["amount"]},
            )

        self.stdout.write("Seeding app settings...")
        for s in SETTINGS_DATA:
            AppSettings.objects.get_or_create(key=s["key"], defaults={"value": s["value"]})

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
