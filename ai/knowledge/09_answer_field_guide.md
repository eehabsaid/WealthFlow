# Answer Field Guide — Which Tool Field Answers Which Question

Applies to `query_application_data`. Each top-level key is a separate module. Read the field below; never copy a number from a different field or module.

## General rules (all modules)
- A yearly, monthly or category total is NOT a single entry. Never present a total as one payment, one expense or one balance.
- `recent_*` lists and `items` show only a capped window of the newest rows. Rows outside that window are not listed. Never guess them: say the requested period is not in the returned data, and suggest a narrower question.
- Lists named `recent_monthly_timeline` are oldest-first (last item = newest). `recent_expenses` is newest-first (first item = newest). Check the `*_note` field next to each list.
- Quote formatted values (`*_formatted`) exactly, with year, month and company or category as given.
- If a requested item truly is absent, say so plainly. Do not use another module or period as a stand-in.
- Data from tools always overrides learned notes and earlier chat answers.

## Salary (`salary`)
- Latest / last paid salary -> `latest_paid_salary_answer` if present, else `latest_salary_entry.paid_formatted`.
- Salary of a specific month (e.g. July 2026) -> `requested_period_answer` (quote it verbatim; it also covers old months outside the timeline window). Fallback: the row in `recent_monthly_timeline` with that `year` and `month`.
- Yearly total -> the matching row in `yearly_summary` (`total_paid`). `latest_active_year_summary` is a yearly total, not a salary.
- `summary.total_paid_all_time` and `company_breakdown` are lifetime totals.

## Expenses (`expenses`)
- Latest expense -> first item of `recent_expenses`.
- Total for the latest month -> `latest_month_summary`; other months -> matching row in `monthly_summary`.
- Spending per category -> `category_breakdown`.

## Balance (`balance`), Bank Certificates (`bank_certificates`), Fixed Assets (`fixed_assets`)
- Totals -> `summary`. A single account, certificate or asset -> the matching entry in `items` (by name, bank or id).
- Certificates: use `amount_in_home_currency` when comparing across currencies.

## Market data (`market_data`)
- Exchange rate -> the row in `exchange_rates` with that `currency_code` (`mid_rate`, `buy_rate`, `sell_rate`).
- Gold price -> `latest_gold_price`.

## Budgets and recurring payments (`budgets`)
- A budget's status -> the matching item in `budgets`. `amount_base` is the limit, `spent_base` what was spent this period, `remaining_base` what is left and `percent_used` the share used; all are in the user's base currency.
- Over the limit -> budgets with `percent_used` of 100 or more. Close to the alert level -> `percent_used` at or above `alert_threshold_percent`. Ignore budgets with `is_active` false.
- Subscriptions and bills -> `recurring_transactions` with `is_active` true: `next_run_date` is the next due date, `frequency` and `interval` say how often, and `amount` is in that item's own `currency_code` (not necessarily the base currency).

## Financial advisor (`financial_advisor`)
- Use the values already computed under `overview` and `opportunity_detection`. Do not recompute them from other modules.
