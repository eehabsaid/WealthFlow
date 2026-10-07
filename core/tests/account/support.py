"""Shared fixture: two users, each with data in the tables that are hardest to scope."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from core.models import (AIConversation, AIMessage, AIPrompt, AIPromptCategory, BalanceEntry, Bank, Currency,
                         CurrencyExchange, Document, FixedAsset)

User = get_user_model()


def make_user_with_data(name, password="Pass12345!"):
    user = User.objects.create_user(username=name, email=f"{name}@example.com", password=password)
    cur, _ = Currency.objects.get_or_create(owner=user, code="EGP", defaults={"name": f"Pound {name}"})
    usd, _ = Currency.objects.get_or_create(owner=user, code="USD", defaults={"name": f"Dollar {name}"})
    bank = Bank.objects.create(owner=user, name=f"Bank {name}")
    a = BalanceEntry.objects.create(owner=user, title=f"{name} cash", balance_type=BalanceEntry.BalanceType.CASH, currency=cur, amount=1000)
    b = BalanceEntry.objects.create(owner=user, title=f"{name} bank", balance_type=BalanceEntry.BalanceType.BANK, bank=bank, currency=usd, amount=5)
    CurrencyExchange.objects.create(
        exchange_date=date(2026, 1, 1), from_balance=a, to_balance=b, from_currency=cur, to_currency=usd,
        from_amount=Decimal("500"), to_amount=Decimal("10"), exchange_rate=Decimal("50"), user=user,
        status=CurrencyExchange.Status.ACTIVE)
    asset = FixedAsset.objects.create(owner=user, name=f"{name} villa", asset_type="Real Estate", purchase_date=date(2024, 1, 1))
    Document.objects.create(
        parent_object_type="fixed_asset", content_type=ContentType.objects.get_for_model(FixedAsset), object_id=asset.id,
        original_file_name=f"{name}.pdf", mime_type="application/pdf", file_size=3, file_content=b"abc", uploaded_by=user)
    cat, _ = AIPromptCategory.objects.get_or_create(code="acct_test", defaults={"name": "Acct test"})
    AIPrompt.objects.create(user=user, name=f"{name} prompt", content="hi", category=cat)
    conv = AIConversation.objects.create(user=user)
    AIMessage.objects.create(conversation=conv, role="user", content=f"secret of {name}")
    return user
