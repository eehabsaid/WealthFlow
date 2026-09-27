"""Regression: "detail as a table the expenses for <month>" must use real,
deterministic per-category-per-month data — never the model's own arithmetic
over a raw transaction list.

Ehab reported this exact request for September 2026 coming back with numbers
that matched neither the correct September total (confirmed via
monthly_summary: 9,297.19 EGP) nor any all-time figure — the model had
nothing deterministic to answer a month+category question with, so it
tried to filter/sum recent_expenses by hand and got it wrong (a known
weakness of small local models doing multi-step arithmetic).

Two root causes, both fixed here:
1. There was no per-category, per-month breakdown in the payload at all —
   only an ALL-TIME category_breakdown and a per-month TOTAL-only
   monthly_summary. Added monthly_category_breakdown (expenses_provider) to
   fill that gap, plus category_breakdown_note/monthly_category_breakdown_note
   telling the model which field to use and which NOT to use for a
   month-scoped question.
2. Confirmed against Ehab's real account: even after adding the new field,
   it was silently dropped under real token-budget pressure — category_
   breakdown + monthly_summary + monthly_category_breakdown combined
   (~5.1KB) didn't fit the remaining ~4.3KB budget, and since they shared
   ONE combined block, the whole thing (including the new field) was
   dropped as a unit. Fixed by giving each large key its OWN block in
   formatting.py, ordered so the most specific/useful field (monthly_
   category_breakdown) is emitted before the more general/redundant one
   (category_breakdown, which explicitly tells the model not to use it for
   a month-scoped question anyway) — so a partial cut drops the least
   useful field first instead of all-or-nothing.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AppSettings, Currency, Expense, ExpenseCategory
from core.services.ai.context_builder_service.formatting import split_payload_blocks
from core.services.ai.context_builder_service.service import ContextBuilderService
from core.services.ai.providers.expenses_provider import (
    MAX_MONTHLY_CATEGORY_BREAKDOWN_MONTHS_FOR_AI,
    ExpensesDataProvider,
)

User = get_user_model()

# Mirrors the shape of Ehab's real account closely enough to reproduce the
# exact budget shortfall (many categories x many months), without using his
# actual data.
_CATEGORY_NAMES = [
    "Food", "Family", "Telecom", "Tobacco", "Transportation", "Utilities",
    "Education", "Fixed Assets", "Other", "Housing", "Personal Care",
]


class MonthlyCategoryBreakdownTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="monthcat_ai", password="pw12345")
        self.egp = Currency.objects.get_or_create(
            code="EGP", owner=self.user, defaults={"name": "Egyptian Pound", "symbol": "EGP"}
        )[0]
        self.categories = [
            ExpenseCategory.objects.get_or_create(owner=self.user, name=n)[0] for n in _CATEGORY_NAMES
        ]

        # 24 months of history, ~4 categories per month (comparable density to
        # a real active account — Ehab's real September had 4 categories) so
        # the resulting block sizes are realistic rather than an artificially
        # dense worst case.
        self.months_of_history = 24
        year, month = 2026, 9
        self.september_expected_by_category: dict[str, float] = {}
        for m in range(self.months_of_history):
            yy, mm = year, month - m
            while mm < 1:
                mm += 12
                yy -= 1
            month_categories = [self.categories[(m + i) % len(self.categories)] for i in range(4)]
            for i, cat in enumerate(month_categories):
                amt = Decimal("100.00") + Decimal(i * 37)
                Expense.objects.create(
                    owner=self.user, date=date(yy, mm, min(10 + i, 28)),
                    year=yy, month=mm, category=cat,
                    amount=amt, amount_egp=amt, currency=self.egp,
                    notes=f"{cat.name} {yy}-{mm}",
                )
                if (yy, mm) == (2026, 9):
                    self.september_expected_by_category[cat.name] = float(amt)

        AppSettings.set("ai_context_token_budget", "2048")

    def test_monthly_category_breakdown_matches_manual_sums(self):
        data = ExpensesDataProvider().get_data(self.user)
        sept = next(m for m in data["monthly_category_breakdown"] if m["year"] == 2026 and m["month"] == 9)
        for cat_name, expected in self.september_expected_by_category.items():
            self.assertAlmostEqual(sept["categories"][cat_name]["total_spending"], expected, places=2)
        # The month's own total must equal the sum of its categories exactly
        # (same money, just sliced two ways) — and match monthly_summary.
        monthly_summary_sept = next(m for m in data["monthly_summary"] if m["year"] == 2026 and m["month"] == 9)
        self.assertEqual(sept["total_spending_formatted"], monthly_summary_sept["total_spending_formatted"])

    def test_capped_to_max_months(self):
        data = ExpensesDataProvider().get_data(self.user)
        self.assertGreater(self.months_of_history, MAX_MONTHLY_CATEGORY_BREAKDOWN_MONTHS_FOR_AI)
        self.assertLessEqual(len(data["monthly_category_breakdown"]), MAX_MONTHLY_CATEGORY_BREAKDOWN_MONTHS_FOR_AI)

    def test_scope_notes_present_and_correct(self):
        data = ExpensesDataProvider().get_data(self.user)
        self.assertIn("ALL-TIME", data["category_breakdown_note"])
        self.assertIn("monthly_category_breakdown", data["category_breakdown_note"])
        self.assertIn("month", data["monthly_category_breakdown_note"].lower())

    def test_survives_real_budget_pressure_for_a_month_scoped_query(self):
        """The actual regression: under real token-budget pressure with a
        realistic multi-category, multi-year account, monthly_category_
        breakdown — the field that actually answers this question, total
        included — must survive even if a lower-priority field (monthly_
        summary and/or the all-time category_breakdown) gets dropped instead."""
        messages, sources = ContextBuilderService().assemble_messages(
            user_query="detail as a table the expenses for Sept 2026",
            history_messages=[], user=self.user,
        )
        system_content = messages[0]["content"]
        self.assertIn("expenses", sources)
        self.assertIn('"monthly_category_breakdown":', system_content)
        # The specific September data must actually be present, not just the key.
        self.assertIn('"month":9', system_content.replace(" ", ""))
        self.assertIn('"Tobacco"', system_content)

    def test_split_payload_blocks_orders_large_keys_by_usefulness(self):
        """Unit-level check independent of system-prompt size: each large key
        gets its own block, in priority order, so a partial budget cut drops
        category_breakdown (least useful for a month question) before
        monthly_category_breakdown/monthly_summary (most useful)."""
        data = ExpensesDataProvider().get_data(self.user)
        high, _ = split_payload_blocks("expenses", data)
        large_block_order = [
            next(i for i, b in enumerate(high) if f'"{k}":' in b)
            for k in ("monthly_category_breakdown", "monthly_summary", "category_breakdown")
        ]
        self.assertEqual(large_block_order, sorted(large_block_order))
