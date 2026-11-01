# Expenses
- Model: `core/models/expenses.py` (`Expense`, `ExpenseCategory`, `ExpenseSubcategory`). `Expense` has owner, date, year, month, category, amount, `amount_base`, `exchange_rate`, currency, bank, payment_method (Cash / Card / Bank Transfer / Other).
- Write ONLY through `ExpenseService.create_expense / update_expense / delete_expense(…, owner)` in `core/services/expenses/expense_service.py`: they check ownership, convert currency (`CurrencyConversionService.strict_rate`) and adjust the balance in one transaction.
- Errors are `ValueError` codes: `bank_account_required`, `category_not_found`, `matching_balance_entry_not_found`, `insufficient_balance`, `readonly_mirrored_expense`, `exchange_rate_missing`.
- Rows with `source_type` set are read-only mirrors of fixed-asset records: they cannot be edited or deleted directly.
- Views: `core/views/expense_views.py`, `expense_category_views.py`, `expense_summary_views.py`. Frontend: `static/js/expenses/`.
- Tests: `core/tests/expenses/`; E2E: `tests/modules/expenses/`.
