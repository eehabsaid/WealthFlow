"""Shared fixtures for the AI investigator tests: users, two-tenant data and a scripted provider."""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model

from core.models import Bank, Company, Currency, Expense, ExpenseCategory, FixedAsset, SalaryEntry

User = get_user_model()


def make_user(name: str, sysadmin: bool = False, django_superuser: bool = False):
    """sysadmin = the app's own tier (profile.is_sysadmin); django_superuser is deliberately independent of it."""
    make = User.objects.create_superuser if django_superuser else User.objects.create_user
    user = make(username=name, password="pw123456", email=f"{name}@x.io")
    if sysadmin:
        from core.authentication.services import AuthWorkflowService

        profile = AuthWorkflowService.get_profile(user)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
    return user


def seed_tenant(user, tag: str, expenses: int = 3, amount: str = "10.00"):
    """One company + salary row + bank + asset + N expenses owned (directly or via parents) by `user`."""
    cur = Currency.objects.create(owner=user, code=f"C{tag}"[:3].upper(), name=f"Cur {tag}")
    bank = Bank.objects.create(owner=user, name=f"Bank {tag}")
    company = Company.objects.create(owner=user, name=f"Co {tag}", display_name=f"Co {tag}")
    SalaryEntry.objects.create(company=company, year=2026, month="9")
    cat = ExpenseCategory.objects.create(owner=user, name=f"Cat {tag}")
    for i in range(expenses):
        Expense.objects.create(owner=user, date=datetime.date(2026, 9, 1 + i), year=2026, month=9, category=cat,
                               amount=Decimal(amount), amount_base=Decimal(amount), currency=cur, bank=bank,
                               description=f"{tag} expense {i}")
    FixedAsset.objects.create(owner=user, name=f"Asset {tag}", asset_type="real_estate", purchase_date=datetime.date(2025, 1, 1))
    return {"currency": cur, "bank": bank, "company": company, "category": cat}


class ScriptedProvider:
    """provider.generate() replays `script` (dicts: content/tool_calls/error) and records every call."""

    supports_tools = True

    def __init__(self, script):
        self.script, self.calls, self.model = list(script), [], "scripted"

    def generate(self, messages, tools=None, **kwargs):
        self.calls.append({"messages": [dict(m) for m in messages], "tools": tools, "kwargs": kwargs})
        item = self.script.pop(0) if self.script else {"content": "(script exhausted)"}
        return {"content": item.get("content", ""), "tool_calls": item.get("tool_calls") or [], "error": item.get("error"),
                "prompt_tokens": 1, "completion_tokens": 1}


def tool_call(name: str, **args) -> dict:
    return {"tool_calls": [{"function": {"name": name, "arguments": args}}]}
