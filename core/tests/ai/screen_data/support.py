"""Fixtures of the screen-data tests: two tenants with different cash and a certificate that matures inside the projection."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from core.models import BalanceEntry, Bank, BankCertificate, Currency
from core.tests.ai.investigation.support import make_user

TODAY = date.today()
TARGET = TODAY + timedelta(days=40)


def tenant(name: str, cash: str, usd: str = "0", sysadmin: bool = False):
    """A user with EGP cash `cash`, optional USD cash and one monthly-interest certificate maturing in 20 days."""
    user = make_user(name, sysadmin=sysadmin)
    egp = Currency.objects.get_or_create(owner=user, code="EGP", defaults={"symbol": "£", "name": "Egyptian Pound"})[0]
    bank = Bank.objects.create(owner=user, name=f"Bank {name}")
    BalanceEntry.objects.create(owner=user, title="Cash", balance_type=BalanceEntry.BalanceType.CASH, currency=egp, bank=bank, amount=Decimal(cash))
    if Decimal(usd):
        usd_cur = Currency.objects.get_or_create(owner=user, code="USD", defaults={"symbol": "$", "name": "US Dollar"})[0]
        BalanceEntry.objects.create(owner=user, title="USD", balance_type=BalanceEntry.BalanceType.CASH, currency=usd_cur, amount=Decimal(usd))
    BankCertificate.objects.create(owner=user, bank=bank, currency=egp, issue_date=TODAY - timedelta(days=100), expiry_date=TODAY + timedelta(days=20),
                                   amount=Decimal("50000"), interest_value=Decimal("500"), frequency="Monthly", status="Active")
    return user
