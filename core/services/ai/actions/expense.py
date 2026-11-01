"""Expense actions (add / edit / delete). Every write goes through ExpenseService, the same code the Expenses screen uses."""

from __future__ import annotations

import datetime

from core.models import Bank, Currency, Expense, ExpenseCategory, ExpenseSubcategory
from core.services.expenses.expense_service import ExpenseService
from core.services.shared.base_currency import get_user_base_code

from .common import ActionError, changed_rows, iso_date, money, one_of, pick_by_name

METHODS = {"cash": "Cash", "card": "Card", "bank transfer": "Bank Transfer", "other": "Other"}
ERRORS = {
    "bank_account_required": "This payment method needs a bank account.",
    "category_not_found": "That category does not exist.",
    "matching_balance_entry_not_found": "There is no balance entry to take this payment from.",
    "insufficient_balance": "The balance is too low for this amount.",
    "readonly_mirrored_expense": "This expense mirrors a fixed-asset record and cannot be changed here.",
    "exchange_rate_missing": "No exchange rate is available for this currency and date.",
}


def _row(e: Expense) -> dict:
    return {"id": e.id, "date": e.date.isoformat(), "amount": str(e.amount), "currency": e.currency.code if e.currency_id else "",
            "category": e.category.name if e.category_id else "", "subcategory": e.subcategory.name if e.subcategory_id else "",
            "description": e.description, "payment_method": e.payment_method, "bank": e.bank.name if e.bank_id else ""}


def _label(r: dict) -> str:
    return f"#{r['id']} {r['date']} {r['amount']} {r['currency']} {r['description']}".strip()


def _clean(user, values: dict, current: dict | None = None) -> tuple[dict, dict]:
    """(service data, human fields) from what the model sent; unknown names raise ActionError with the valid choices."""
    data, human = {}, {}
    if "amount" in values:
        amount = money(values["amount"])
        data["amount"], human["amount"] = amount, str(amount)
    if "date" in values:
        data["date"] = human["date"] = iso_date(values["date"])
    for key in ("description", "notes"):
        if key in values:
            data[key] = human[key] = " ".join(str(values[key] or "").split())[:300]
    if "payment_method" in values:
        method = METHODS.get(str(values["payment_method"]).strip().lower())
        if not method:
            raise ActionError("`payment_method` must be Cash, Card, Bank Transfer or Other")
        data["payment_method"] = human["payment_method"] = method
    if "currency" in values:
        cur = Currency.objects.filter(owner=user, code__iexact=str(values["currency"]).strip()).first()
        if cur is None:
            raise ActionError(f"unknown currency '{values['currency']}'. Use one of: " + ", ".join(Currency.objects.filter(owner=user).values_list("code", flat=True)))
        data["currency_id"], human["currency"] = cur.id, cur.code
    if "bank" in values:
        bank = pick_by_name(Bank.objects.filter(owner=user, is_active=True), values["bank"], "bank")
        data["bank_id"], human["bank"] = bank.id, bank.name
    if "category" in values:
        cat = pick_by_name(ExpenseCategory.objects.filter(owner=user), values["category"], "category")
        data["category_id"], human["category"] = cat.id, cat.name
        if "subcategory" not in values:
            data["subcategory_id"], human["subcategory"] = None, ""
    if "subcategory" in values:
        cat_id = data.get("category_id") or (current or {}).get("category_id")
        if not cat_id:
            raise ActionError("give the `category` together with the `subcategory`")
        sub = pick_by_name(ExpenseSubcategory.objects.filter(category_id=cat_id, category__owner=user), values["subcategory"], "subcategory")
        data["subcategory_id"], human["subcategory"] = sub.id, sub.name
    return data, human


def find(user, target: dict) -> Expense:
    qs = Expense.objects.filter(owner=user).select_related("currency", "category", "subcategory", "bank")
    if target.get("id"):
        qs = qs.filter(pk=target["id"])
    else:
        if target.get("date"):
            qs = qs.filter(date=iso_date(target["date"], "target.date"))
        if target.get("amount"):
            qs = qs.filter(amount=money(target["amount"], "target.amount"))
        if target.get("description"):
            qs = qs.filter(description__icontains=str(target["description"]).strip())
        if not any(target.get(k) for k in ("date", "amount", "description")):
            raise ActionError("say which expense: target.id, or its date / amount / description")
    rows = [dict(_row(e), label=_label(_row(e))) for e in qs.order_by("-date", "-id")[:6]]
    picked = one_of(rows, "expense")
    return qs.get(pk=picked["id"])


def propose(user, op: str, target: dict, values: dict) -> dict:
    if op == "add":
        values = {"payment_method": "Cash", "date": datetime.date.today().isoformat(), **{k: v for k, v in values.items() if v not in (None, "")}}
        if "amount" not in values:
            raise ActionError("an expense needs an `amount`")
        if "currency" not in values:
            values["currency"] = get_user_base_code(user)
        data, human = _clean(user, values)
        data["currency_id"] = data.get("currency_id")
        return {"record": "expense", "op": "add", "params": {"data": _jsonable(data)}, "rows": [{"label": k, "value": v} for k, v in human.items()]}
    exp = find(user, target)
    current = _row(exp)
    if op == "delete":
        return {"record": "expense", "op": "delete", "params": {"id": exp.id}, "rows": [{"label": k, "value": str(v)} for k, v in current.items() if v not in ("", None) and k != "id"]}
    data, human = _clean(user, values, {"category_id": exp.category_id})
    rows = changed_rows(current, human)
    if not rows:
        raise ActionError("nothing would change; ask the user what to change")
    return {"record": "expense", "op": "edit", "params": {"id": exp.id, "data": _jsonable(data)}, "rows": rows}


def _jsonable(data: dict) -> dict:
    return {k: (str(v) if k == "amount" else v) for k, v in data.items()}


def execute(user, op: str, params: dict) -> str:
    try:
        if op == "add":
            data = dict(params["data"])
            exp = ExpenseService.create_expense(data, user)
            return f"Expense #{exp.id} added."
        if op == "edit":
            from decimal import Decimal
            data = dict(params["data"])
            if "amount" in data:
                data["amount"] = Decimal(data["amount"])
            ExpenseService.update_expense(params["id"], data, user)
            return f"Expense #{params['id']} updated."
        ExpenseService.delete_expense(params["id"], user)
        return f"Expense #{params['id']} deleted."
    except ValueError as exc:
        raise ActionError(ERRORS.get(str(exc), "The expense could not be saved.")) from None
    except Expense.DoesNotExist:
        raise ActionError("That expense no longer exists.") from None
