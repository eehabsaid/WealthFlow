"""Shared fixtures for the query-engine chat tests: two tenants, market data, and data for every capability."""

import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model

from core.models import (AppSettings, Bank, BalanceEntry, BankCertificate, Company, Currency, ExchangeRate, Expense,
                         ExpenseCategory, FixedAsset, GoldPrice, SalaryEntry)
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()
CHAT_URL = "/api/financial-advisor/ai/chat/"


def build(test):
    test.user = User.objects.create_user(username="qe_user", password="pw123456")
    test.other = User.objects.create_user(username="qe_other", password="pw123456")
    grant_ai_workspace_access(test.user)
    ExchangeRate.objects.create(currency_code="USD", buy_rate=Decimal("50"), sell_rate=Decimal("50.5"), mid_rate=Decimal("50.25"))
    ExchangeRate.objects.create(currency_code="EUR", buy_rate=Decimal("55"), sell_rate=Decimal("55.5"), mid_rate=Decimal("55.25"))
    GoldPrice.objects.create(carat_24k=Decimal("5000"), carat_21k=Decimal("4375"), carat_18k=Decimal("3750"), carat_22k=Decimal("4583"),
                             carat_24k_buy=Decimal("4950"), carat_21k_buy=Decimal("4300"), carat_18k_buy=Decimal("3700"),
                             usd_gram_24k=Decimal("100"), usd_per_oz=Decimal("3110.35"), usd_to_egp=Decimal("50"))
    for owner, marker in ((test.user, ""), (test.other, "SECRET")):
        egp = Currency.objects.get_or_create(owner=owner, code="EGP", defaults={"name": "Egyptian Pound"})[0]
        bank = Bank.objects.create(owner=owner, name=f"{marker}NBE Bank")
        BalanceEntry.objects.create(owner=owner, title="Main", balance_type="bank", bank=bank, currency=egp, amount=Decimal("1000.00" if not marker else "777777.00"))
        cat = ExpenseCategory.objects.create(owner=owner, name=f"{marker}Food")
        for m, d, amt, desc in ((6, 1, "100.00", "Rice"), (6, 2, "50.50", "Milk"), (8, 5, "20.00", "Tea"), (9, 1, "1000.00", "Rent")):
            Expense.objects.create(owner=owner, category=cat, date=date(2026, m, d), year=2026, month=m, amount=amt, amount_base=amt, description=desc)
        co = Company.objects.create(owner=owner, name="Acme", display_name="Acme")
        SalaryEntry.objects.create(company=co, year=2026, month="January", paid="87643.86" if not marker else "111.00", expected="90000")
        # bulk_create: the certificate pre_save signal would demand (and deduct from) a cash balance entry
        BankCertificate.objects.bulk_create([BankCertificate(owner=owner, bank=bank, currency=egp, amount=Decimal("100000" if not marker else "999999"), interest_rate=Decimal("20"),
                                       interest_value=Decimal("1666.67"), frequency="monthly", status="Active",
                                       issue_date=date.today() - timedelta(days=30), expiry_date=date.today() + timedelta(days=700))])
        FixedAsset.objects.create(owner=owner, name=f"{marker}Villa", asset_type="Real Estate", purchase_date=date(2024, 1, 1),
                                  purchase_price=Decimal("5000000" if not marker else "9999999"), current_market_value=Decimal("5000000" if not marker else "9999999"))
    AppSettings.set("ai_enabled", "true")
    AppSettings.set("ai_provider", "ollama")
    test.client.force_login(test.user)


def ask(test, text, conversation=True):
    """Posts like the UI: after the first message the same conversation_id is sent (kept on `test`)."""
    body = {"message": text}
    if conversation and getattr(test, "_conversation_id", None):
        body["conversation_id"] = test._conversation_id
    data = test.client.post(CHAT_URL, json.dumps(body), content_type="application/json").json()
    if conversation:
        test._conversation_id = data.get("conversation_id") or getattr(test, "_conversation_id", None)
    return data
