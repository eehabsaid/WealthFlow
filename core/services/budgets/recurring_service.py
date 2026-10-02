"""Recurring transactions: CRUD plus posting due occurrences as real
Expense rows through the existing ExpenseService (so balance deduction,
currency conversion, and category totals all stay consistent with
manually-entered expenses — no parallel bookkeeping logic here).
"""
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction

from core.models import RecurringTransaction


def _advance(current: date, frequency: str, interval: int) -> date:
    interval = max(1, int(interval or 1))
    if frequency == "daily":
        return current + timedelta(days=interval)
    if frequency == "weekly":
        return current + timedelta(weeks=interval)
    if frequency == "yearly":
        return current + relativedelta(years=interval)
    return current + relativedelta(months=interval)  # monthly (default)


class RecurringService:
    @staticmethod
    @transaction.atomic
    def create_recurring(data, owner) -> RecurringTransaction:
        start = date.fromisoformat(data["start_date"])
        next_run = start
        if not data.get("backfill_missed"):
            # Default: never post history. Skip occurrences before today so the
            # first posting is the next one on or after today.
            today = date.today()
            safety = 0
            while next_run < today and safety < 3660:
                next_run = _advance(next_run, data.get("frequency", "monthly"), int(data.get("interval", 1)))
                safety += 1
        return RecurringTransaction.objects.create(
            owner=owner,
            name=data["name"],
            category_id=data.get("category_id"),
            subcategory_id=data.get("subcategory_id"),
            amount=Decimal(str(data.get("amount", 0) or 0)),
            currency_id=data.get("currency_id"),
            payment_method=data.get("payment_method", "Cash"),
            bank_id=data.get("bank_id"),
            frequency=data.get("frequency", "monthly"),
            interval=int(data.get("interval", 1)),
            start_date=start,
            next_run_date=next_run,
            end_date=date.fromisoformat(data["end_date"]) if data.get("end_date") else None,
            is_active=data.get("is_active", True),
            notes=data.get("notes", ""),
        )

    @staticmethod
    @transaction.atomic
    def update_recurring(rec: RecurringTransaction, data) -> RecurringTransaction:
        for field in ("name", "payment_method", "frequency", "notes"):
            if field in data:
                setattr(rec, field, data[field])
        for field in ("category_id", "subcategory_id", "currency_id", "bank_id"):
            if field in data:
                setattr(rec, field, data[field])
        if "amount" in data:
            rec.amount = Decimal(str(data["amount"] or 0))
        if "interval" in data:
            rec.interval = int(data["interval"])
        if "is_active" in data:
            rec.is_active = data["is_active"]
        if "end_date" in data:
            rec.end_date = date.fromisoformat(data["end_date"]) if data["end_date"] else None
        if "next_run_date" in data:
            rec.next_run_date = date.fromisoformat(data["next_run_date"])
        rec.save()
        return rec

    @staticmethod
    def preview_due(owner, as_of: date = None):
        """Read-only list of the occurrences process_due() would post right
        now. Nothing is written."""
        as_of = as_of or date.today()
        items = []
        for rec in RecurringTransaction.objects.filter(
            owner=owner, is_active=True, next_run_date__lte=as_of
        ).select_related("currency"):
            run_date = rec.next_run_date
            safety = 0
            while run_date <= as_of and safety < 366:
                safety += 1
                if rec.end_date and run_date > rec.end_date:
                    break
                items.append({
                    "recurring_id": rec.id,
                    "name": rec.name,
                    "date": run_date.isoformat(),
                    "amount": float(rec.amount),
                    "currency_code": rec.currency.code if rec.currency else rec._default_currency_code(),
                })
                run_date = _advance(run_date, rec.frequency, rec.interval)
        return items

    @staticmethod
    @transaction.atomic
    def process_due(owner, as_of: date = None):
        """Post every due, active recurring transaction for `owner` as a
        real Expense and advance its next_run_date. Returns the list of
        created Expense objects. Idempotent per call: a recurring item
        with next_run_date in the future after this run is left alone
        until it's due again."""
        from core.services.expenses.expense_service import ExpenseService

        as_of = as_of or date.today()
        created = []
        skipped = []
        due_qs = RecurringTransaction.objects.filter(
            owner=owner, is_active=True, next_run_date__lte=as_of
        )
        for rec in due_qs:
            # Guard against an end_date reached mid-loop.
            safety = 0
            while rec.next_run_date <= as_of and safety < 366:
                safety += 1
                if rec.end_date and rec.next_run_date > rec.end_date:
                    rec.is_active = False
                    break
                try:
                    expense = ExpenseService.create_expense(
                        {
                            "date": rec.next_run_date.isoformat(),
                            "category_id": rec.category_id,
                            "subcategory_id": rec.subcategory_id,
                            "description": rec.name,
                            "amount": float(rec.amount),
                            "currency_id": rec.currency_id,
                            "bank_id": rec.bank_id,
                            "payment_method": rec.payment_method,
                            "notes": rec.notes,
                        },
                        owner,
                    )
                except ValueError as exc:
                    # Leave next_run_date where it is so this occurrence is
                    # retried next time process_due runs, instead of silently
                    # skipping it forward (e.g. insufficient_balance today).
                    skipped.append({"recurring_id": rec.id, "reason": str(exc)})
                    break
                created.append(expense)
                rec.last_run_date = rec.next_run_date
                rec.next_run_date = _advance(rec.next_run_date, rec.frequency, rec.interval)
            rec.save()
        return created, skipped
