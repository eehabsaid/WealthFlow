import json
from django.core.management.base import BaseCommand
from core.models import Company, SalaryEntry, Bank, BalanceEntry, AppSettings, Currency

COMPANIES = [
    {"name": "NTG",                "display_name": "NTG",                "group_name": "NTG",          "color_hex": "#17a2b8", "order": 1},
    {"name": "Giza Systems",       "display_name": "Giza Systems",       "group_name": "Giza Systems", "color_hex": "#0d6efd", "order": 2},
    {"name": "Giza Systems (2)",   "display_name": "Giza Systems (2)",   "group_name": "Giza Systems", "color_hex": "#0d6efd", "order": 3},
    {"name": "ElSewedyTechnology", "display_name": "ElSeweedy Technology","group_name": "ElSeweady",   "color_hex": "#fd7e14", "order": 4},
    {"name": "Dedalus",            "display_name": "Dedalus",            "group_name": "Dedalus",      "color_hex": "#6610f2", "order": 5},
    {"name": "Globemed",           "display_name": "Globemed",           "group_name": "Globemed",     "color_hex": "#20c997", "order": 6},
    {"name": "Giza Systems (3)",   "display_name": "Giza Systems (3)",   "group_name": "Giza Systems", "color_hex": "#0d6efd", "order": 7},
]

# Each tuple: (year, month, expected, paid) or (year, month, expected, paid, bonus)
SALARY_DATA = {
    "NTG": [
        (2008,"September",1700,1700),(2008,"October",1700,1700),
        (2008,"November",1800,1800),(2008,"December",1900,1900),
        (2009,"January",2000,2000),(2009,"February",2000,2000),
        (2009,"March",2000,2000),(2009,"April",2000,2000),
        (2009,"May",2000,2000),(2009,"June",2000,2000),
        (2009,"July",2500,2500),(2009,"August",2500,2500),
        (2009,"September",2500,2500),(2009,"October",2500,2500),
        (2009,"November",2500,2500),(2009,"December",2500,2500),
        (2010,"January",2500,2500),(2010,"February",2500,2500),
        (2010,"March",2500,2500),(2010,"April",2500,2500),
        (2010,"May",2500,2500),(2010,"June",2500,2500),
        (2010,"July",3000,3000),(2010,"August",3000,3000),
        (2010,"September",3000,3000),(2010,"October",3000,3000),
        (2010,"November",3000,3000),(2010,"December",3000,3000),
        (2011,"January",3300,3300),(2011,"February",3300,3300),
        (2011,"March",3300,3300),(2011,"April",3300,3300),
        (2011,"May",3300,3300),(2011,"June",3300,3300),
        (2011,"July",3300,3300),(2011,"August",3300,3300),
        (2011,"September",3800,3800),(2011,"October",3800,3800),
        (2011,"November",3800,3800),(2011,"December",3800,3800),
        (2012,"January",3800,3800),(2012,"February",3800,2800),
        (2012,"March",3800,3800),(2012,"April",3800,3800),
        (2012,"May",3800,3800),(2012,"June",3800,2200),
        (2012,"July",1900,0),
    ],
    "Giza Systems": [
        (2012,"August",5500,5500),(2012,"September",5500,5500),
        (2012,"October",5500,5500),(2012,"November",5500,5500),
        (2012,"December",5500,5500),
        (2013,"January",5500,5500),(2013,"February",5500,5500),
        (2013,"March",5500,5500),(2013,"April",5500,5500),
        (2013,"May",5500,5500),(2013,"June",5500,5500),
        (2013,"July",5500,5500),(2013,"August",5500,5500),
        (2013,"September",5500,5500),(2013,"October",5500,5500),
        (2013,"November",5500,5500),(2013,"December",5500,5500),
        (2014,"January",6700,6700),(2014,"February",6700,6700),
        (2014,"March",6700,6700),(2014,"April",6700,6700),
        (2014,"May",6700,6700),(2014,"June",6700,6700),
        (2014,"July",8620,8620),(2014,"August",8620,8620),
        (2014,"September",8620,8620),(2014,"October",8620,8620),
        (2014,"November",8620,8620),(2014,"December",8620,8620),
        (2015,"January",8620,8620),(2015,"February",8620,8620),
        (2015,"March",8620,8620),
    ],
    "Giza Systems (2)": [
        (2015,"June",8620,8620),(2015,"July",8620,8620),
        (2015,"August",8620,8620),(2015,"September",8620,8620),
        (2015,"October",8620,8620),(2015,"November",8620,8620),
        (2015,"December",8620,8620),
        (2016,"January",10000,10000),(2016,"February",10000,10000),
        (2016,"March",10000,10000),(2016,"April",10000,10000),
        (2016,"May",10000,10000),(2016,"June",10000,10000),
        (2016,"July",10000,10000),(2016,"August",10000,10000),
        (2016,"September",10000,10000),(2016,"October",10000,10000),
        (2016,"November",10000,10000),(2016,"December",10000,10000),
        (2017,"January",14000,14000),(2017,"February",14000,14000),
        (2017,"March",14000,14000),(2017,"April",14000,14000),
        (2017,"May",14000,14000),(2017,"June",14000,14000),
        (2017,"July",14000,14000),(2017,"August",14000,14000),
        (2017,"September",14000,14000),(2017,"October",14000,14000),
        (2017,"November",14000,14000),(2017,"December",14000,14000),
        (2018,"January",17500,17500),(2018,"February",17500,17500),
        (2018,"March",17500,17500),(2018,"April",17500,17500),
        (2018,"May",17500,17500),(2018,"June",17500,17500),
        (2018,"July",17500,17500),(2018,"August",17500,17500),
        (2018,"September",17500,17500),(2018,"October",17500,17500),
        (2018,"November",17500,17500),(2018,"December",17500,17500),
        (2019,"January",20002,20002),(2019,"February",20002,20002),
        (2019,"March",20002,20002),(2019,"April",20002,20002),
        (2019,"May",20002,20002),
    ],
    "ElSewedyTechnology": [
        (2021,"April",24000,24000),(2021,"May",24000,24000),
        (2021,"June",24000,24000),(2021,"July",24000,24000),
        (2021,"August",24000,24000),(2021,"September",24000,24000),
        (2021,"October",24000,24000),(2021,"November",24000,24000),
        (2021,"Quarter-Bonuses",72000,28790),
    ],
    "Dedalus": [
        (2022,"March",29986.62,29986.62),
        (2022,"April",6400.79,6400.79),
    ],
    "Globemed": [
        (2022,"August",22700,22700),
    ],
    "Giza Systems (3)": [
        (2022,"September",35000,35000,0),
        (2022,"October",35000,35000,0),
        (2022,"November",35000,35000,0),
        (2022,"December",35000,42537.48,7537.48),
        (2023,"January",37000,37000,0),(2023,"February",37000,37000,0),
        (2023,"March",37000,37000,0),(2023,"April",37000,37000,0),
        (2023,"May",37000,37000,0),(2023,"June",37000,37000,0),
        (2023,"July",37000,37000,0),(2023,"August",37000,37000,0),
        (2023,"September",37000,37000,0),
        (2023,"October",52000,52000,0),(2023,"November",52000,52000,0),
        (2023,"December",52000,147913.24,95913.24),
        (2024,"January",63440,63440,0),(2024,"February",63440,63440,0),
        (2024,"March",63440,63440,0),(2024,"April",63440,63440,0),
        (2024,"May",63440,63440,0),(2024,"June",63440,63440,0),
        (2024,"July",63440,63440,0),(2024,"August",63440,63440,0),
        (2024,"September",63440,63440,0),
        (2024,"October",63807.22,63807.22,0),
        (2024,"November",63807.22,63807.22,0),
        (2024,"December",63807.22,225291.44,162484.22),
        (2025,"January",77161.91,77161.91,0),(2025,"February",77161.91,77161.91,0),
        (2025,"March",77161.91,77161.91,0),(2025,"April",77161.91,77161.91,0),
        (2025,"May",77972.42,77972.42,0),(2025,"June",77972.42,77972.42,0),
        (2025,"July",77613.61,77613.61,0),(2025,"August",77613.61,77613.61,0),
        (2025,"September",77613.61,77613.61,0),
        (2025,"October",77310.38,77310.38,0),(2025,"November",77310.38,77310.38,0),
        (2025,"December",77310.38,274632.68,197322.30),
        (2026,"January",87643.86,87643.86,0),(2026,"February",87643.86,87643.86,0),
        (2026,"March",87643.86,87643.86,0),(2026,"April",89030.96,89030.96,0),
        (2026,"May",87643.86,0,0),(2026,"June",87643.86,0,0),
        (2026,"July",87643.86,0,0),(2026,"August",87643.86,0,0),
        (2026,"September",87643.86,0,0),(2026,"October",87643.86,0,0),
        (2026,"November",87643.86,0,0),(2026,"December",87643.86,0,0),
    ],
}


CURRENCIES = [
    {"code": "EGP",  "name": "Egyptian Pound",  "symbol": "ج.م", "flag": "🇪🇬", "order": 1},
    {"code": "USD",  "name": "US Dollar",        "symbol": "$",   "flag": "🇺🇸", "order": 2},
    {"code": "EUR",  "name": "Euro",              "symbol": "€",   "flag": "🇪🇺", "order": 3},
    {"code": "SAR",  "name": "Saudi Riyal",       "symbol": "﷼",  "flag": "🇸🇦", "order": 4},
    {"code": "Gold", "name": "Gold (grams)",      "symbol": "g",   "flag": "🥇",  "order": 5},
]

BANKS = [
    {"name": "ENBD", "account_number": "449301732402",  "card_id": "5296072057929610",
     "swift_code": "", "customer_id": "", "customer_name": ""},
    {"name": "QNB",  "account_number": "1130890779776", "card_id": "4738660002749880",
     "swift_code": "QNBAEGCX", "customer_id": "1000925041",
     "customer_name": "IHAB SAIED MOHAMED HASSAN"},
]

BALANCE_DATA = [
    {"title": "Home Balance",              "bank": None,   "currency": "USD",  "amount": 36930},
    {"title": "Home Balance",              "bank": None,   "currency": "EUR",  "amount": 4500},
    {"title": "Home Balance",              "bank": None,   "currency": "SAR",  "amount": 483.25},
    {"title": "Home Balance",              "bank": None,   "currency": "Gold", "amount": 125},
    {"title": "ENBD Bank Account Balance", "bank": "ENBD", "currency": "EGP",  "amount": 268424.61},
    {"title": "QNB Bank Account Balance",  "bank": "QNB",  "currency": "EGP",  "amount": 73813.32},
    {"title": "QNB Certificates Balance",  "bank": "QNB",  "currency": "EGP",  "amount": 3458000},
]

SETTINGS_DATA = [
    {"key": "active_language", "value": "en"},
    {"key": "active_currency", "value": "EGP"},
    {"key": "available_languages", "value": json.dumps([
        {"code": "en", "label": "English", "rtl": False},
        {"code": "ar", "label": "\u0627\u0644\u0639\u0631\u0628\u064a\u0629", "rtl": True},
    ])},
    {"key": "app_title", "value": "WealthFlow"},
]


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
