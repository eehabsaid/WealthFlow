"""Regression: "what is my last expense?" must return the actual latest transaction,
not the current month's total. Ehab reported the AI answering with the September 2026
monthly total instead.

Root cause: monthly_summary (expenses_provider.py) is unbounded — one entry per
(year, month) for the user's ENTIRE history — and lives in the HIGH-priority summary
block that split_payload_blocks() never trims. recent_expenses (the only place a
single transaction lives) is in the LOW-priority block, dropped first under token
budget pressure. On an account with many months of history, the unbounded
monthly_summary array alone can consume the whole data budget and squeeze
recent_expenses out entirely, leaving the model with only monthly aggregates.

This only reproduces with a LARGE monthly_summary (many months of history) that
actually forces budget pressure — a small fixture doesn't trigger it.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AppSettings, Currency, Expense, ExpenseCategory
from core.services.ai.context_builder_service.service import ContextBuilderService
from core.services.ai.providers.expenses_provider import (
    MAX_MONTHLY_SUMMARY_MONTHS_FOR_AI,
    MAX_RECENT_EXPENSES_FOR_AI,
    ExpensesDataProvider,
)

User = get_user_model()


class LastExpenseBudgetPressureTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="lastexp_ai", password="pw12345")
        self.egp = Currency.objects.get_or_create(
            code="EGP", owner=self.user, defaults={"name": "Egyptian Pound", "symbol": "EGP"}
        )[0]
        self.category = ExpenseCategory.objects.get_or_create(owner=self.user, name="Groceries")[0]

        # Force real budget pressure: many months of history (monthly_summary is
        # unbounded pre-fix) with several transactions per month so the payload
        # is actually large, not just many months with one row each.
        self.months_of_history = 60  # 5 years — far beyond a small fixture
        self.last_expense_amount = Decimal("123.45")
        self.last_expense_notes = "THE_ACTUAL_LAST_EXPENSE"

        year, month = 2026, 9
        for m in range(self.months_of_history):
            yy, mm = year, month - m
            while mm < 1:
                mm += 12
                yy -= 1
            for day in (5, 15, 25):
                Expense.objects.create(
                    owner=self.user,
                    date=date(yy, mm, min(day, 28)),
                    year=yy, month=mm,
                    category=self.category,
                    amount=Decimal("50.00"),
                    amount_egp=Decimal("50.00"),
                    currency=self.egp,
                    notes=f"filler {yy}-{mm}-{day}",
                )

        # The single most recent transaction overall — must be identifiable
        # as "the last expense" regardless of what the monthly total shows.
        self.last_expense = Expense.objects.create(
            owner=self.user,
            date=date(2026, 9, 30),
            year=2026, month=9,
            category=self.category,
            amount=self.last_expense_amount,
            amount_egp=self.last_expense_amount,
            currency=self.egp,
            notes=self.last_expense_notes,
        )

        AppSettings.set("ai_context_token_budget", "2048")

    def test_monthly_summary_is_capped_and_still_correct_at_index_0(self):
        data = ExpensesDataProvider().get_data(self.user)
        # Full history is far larger than the cap.
        self.assertGreater(self.months_of_history, MAX_MONTHLY_SUMMARY_MONTHS_FOR_AI)
        self.assertLessEqual(len(data["monthly_summary"]), MAX_MONTHLY_SUMMARY_MONTHS_FOR_AI)
        # latest_month_summary is always the true latest month, capped or not.
        self.assertEqual(data["latest_month_summary"]["year"], 2026)
        self.assertEqual(data["latest_month_summary"]["month"], 9)

    def test_provider_exposes_last_expense_in_high_priority_summary(self):
        data = ExpensesDataProvider().get_data(self.user)
        last = data["summary"]["last_expense"]
        self.assertIsNotNone(last)
        self.assertEqual(last["id"], self.last_expense.id)
        self.assertEqual(last["notes"], self.last_expense_notes)
        self.assertAlmostEqual(last["amount"], float(self.last_expense_amount), places=2)

    def test_last_expense_survives_token_budget_pressure_even_if_details_dropped(self):
        """The actual regression: assemble real AI context messages under the
        default token budget and confirm the marker for the true last expense
        is present in what gets sent to the model — even if the low-priority
        recent_expenses/expenses_details block itself gets dropped."""
        messages, sources = ContextBuilderService().assemble_messages(
            user_query="what is my last expense value?",
            history_messages=[],
            user=self.user,
        )
        system_content = messages[0]["content"]

        self.assertIn("expenses", sources)
        # The single-transaction marker (from summary.last_expense, HIGH priority)
        # must be present in the assembled context.
        self.assertIn(self.last_expense_notes, system_content)
        self.assertIn("123.45", system_content)

    def test_recent_expenses_still_capped_independently(self):
        data = ExpensesDataProvider().get_data(self.user)
        self.assertLessEqual(len(data["recent_expenses"]), MAX_RECENT_EXPENSES_FOR_AI)
        self.assertEqual(data["recent_expenses"][0]["id"], self.last_expense.id)
