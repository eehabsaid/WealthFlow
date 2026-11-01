# Balances and net worth
- `BalanceEntry` (`core/models/balance/balance_entry.py`): owner, title, `balance_type` (cash / bank / gold / certificate), bank, currency, amount (Decimal 18,2).
- Money moves through `core/services/expenses/expense_balance_helpers.py` (`_apply_expense_balance_delta`) and the balance services in `core/services/balance/`. Never change a balance with a raw `.update()` outside these helpers.
- Net worth: `core/services/balance/net_worth_calculations.py` and `net_worth_service/`. These are financial calculations: do not change without approval.
- Cash expenses and bank expenses both reduce a matching `BalanceEntry`; a missing matching entry raises `matching_balance_entry_not_found`, too little money raises `insufficient_balance`.
- Always use `Decimal`, never `float`, for stored money. Amounts are kept in their own currency plus `amount_base` in the user's base currency (`get_user_base_code(owner)`).
- Latest exchange rates: `core/services/shared/latest_rates.latest_exchange_rates()`; never `order_by("-fetched_at").first()` inline.
- Tests: `core/tests/balance/`.
