"""Phase 3: Expenses E2E test. Split out of
scripts/test_all_modules_human_e2e.py."""

from decimal import Decimal

from core.models import ExpenseCategory
from core.services.expenses.expense_service import ExpenseService


def run_expenses_test(ctx):
    # ------------------------------------------------------------------
    # 3. EXPENSES MODULE TEST
    # ------------------------------------------------------------------
    print("\n--- 3. EXPENSES E2E TEST ---")
    cat, _ = ExpenseCategory.objects.get_or_create(name="QA Travel Expenses")
    expense_data = {
        "title": "QA Overseas Hotel Expense",
        "category_id": cat.id,
        "date": "2026-08-05",
        "amount": 150.00,
        "currency_id": ctx.usd.id,
        "payment_method": "cash"
    }
    exp = ExpenseService.create_expense(expense_data)
    exp.refresh_from_db()
    # CurrencyConversionService uses buy_rate (50.0) -> amount_egp = 150 * 50 = 7500.00 EGP
    assert exp.exchange_rate == Decimal("50.000000"), f"Expense rate failed: {exp.exchange_rate}"
    assert exp.amount_egp == Decimal("7500.00"), f"Expense amount_egp failed: {exp.amount_egp}"
    print(f"  [PASS] Expense Creation with Buy Rate: {exp.amount} USD -> {exp.amount_egp} EGP (rate={exp.exchange_rate}).")

    # Update Expense
    update_data = {"amount": 200.00}
    exp = ExpenseService.update_expense(exp.id, update_data)
    exp.refresh_from_db()
    assert exp.amount_egp == Decimal("10000.00"), f"Expense edit amount_egp failed: {exp.amount_egp}"
    print(f"  [PASS] Expense Edit with Buy Rate: updated to {exp.amount} USD -> {exp.amount_egp} EGP.")

    ctx.cat = cat
    ctx.exp = exp
