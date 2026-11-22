"""en / ar / fr / de wording for every answer the engine writes. Code-generated text only: no LLM.
(fr / de tables live in labels_fr.py / labels_de.py; every table has the same keys and {fields}, enforced by tests.)"""

from __future__ import annotations

import calendar

from ai.services.query_engine import labels_de, labels_fr
from .labels_ar import _AR, _AR_MONTHS  # noqa: F401


_EN = {
    "uncategorized": "Uncategorized", "no_date": "No date", "grand": "Grand Total", "total_of": "Total {label}",
    "col_date": "Date", "col_total": "Total", "col_details": "Details", "col_category": "Category", "col_share": "Share",
    "col_tx": "Transactions", "col_month": "Month", "col_desc": "Description", "col_amount": "Amount",
    "col_company": "Company", "col_expected": "Expected", "col_paid": "Paid", "col_bonus": "Bonus",
    "col_account": "Account", "col_type": "Type", "col_bank": "Bank", "col_currency": "Currency", "col_balance": "Balance",
    "col_home": "In {cur}", "col_rate": "Rate", "col_expiry": "Expiry", "col_principal": "Principal",
    "col_interest": "Monthly interest", "col_value": "Value", "col_karat": "Karat", "col_sell": "Sell", "col_buy": "Buy",
    "col_mid": "Mid", "col_name": "Name", "col_days": "Days left", "col_next": "Next interest",
    "head_tx": "{amount} across {n} transactions", "exp_none": "No expenses are recorded for {label}.",
    "exp_total": "Total expenses for {label}: {head}.", "exp_total_cat": "Total expenses for {label} in {cat}: {head}.",
    "exp_daily": "Daily expenses for {label} (total {head}):", "exp_cat": "Expenses by category for {label} (total {head}):",
    "exp_month": "Expenses by month for {label} (total {head}, amounts in {cur}):",
    "exp_table": "Expenses for {label} ({n} transactions, amounts in {cur}):", "exp_empty_note": "No expenses are recorded for: {labels}.",
    "exp_latest": "Latest {n} expense(s) (amounts in {cur}):", "exp_top": "Largest {n} expense(s) for {label} (amounts in {cur}):",
    "exp_avg": "Average monthly expenses for {label}: {amount} (over {n} month(s) with data).",
    "exp_top_cat": "Top spending category for {label}: {name} — {amount} ({share}).",
    "exp_capped": "Showing the first {shown} of {n} transactions; totals include all of them.",
    "sal_none": "No salary entry is recorded for {label}.", "sal_month": "Paid salary for {label}: {parts}.",
    "sal_part": "{amount} from {company}", "sal_latest": "Latest paid salary: {amount} for {month} {year} from {company}.",
    "sal_none_any": "No salary entries are recorded.", "sal_table": "Salary for {label} (amounts in {cur}):",
    "sal_total": "Total {what} for {label}: {amount}.", "sal_avg": "Average monthly {what} for {label}: {amount} (over {n} month(s)).",
    "what_paid": "paid salary", "what_expected": "expected salary", "what_bonus": "bonus",
    "sal_year_table": "Salary by year (amounts in {cur}):", "col_year": "Year", "col_yoy": "Change vs prior year",
    "export_download": "Download as {format}", "export_title": "WealthFlow AI", "export_question": "Question",
    "export_generated": "Generated on {date}", "export_followup": "Download the previous answer:",
    "export_nothing": "There is no earlier answer to export yet. Ask your question first, then ask me to export it.",
    "translate_incomplete": "I could not translate the whole answer completely and reliably (language: {language}), so I am not giving an incomplete translation. Please try again.",
    "bal_total": "Total balance: {amount} across {n} account(s).", "bal_gold": "Gold holdings: {grams} g, worth {amount}.",
    "bal_gold_note": "Gold is included in the total ({amount}).", "bal_none": "No balance accounts are recorded.",
    "bal_cur": "Balance in {cur}: {amount} across {n} account(s) (≈ {home}).", "bal_cur_none": "No {cur} balance is recorded.",
    "bal_bank": "Balance at {bank}: {home} across {n} account(s).", "bal_bank_none": "No accounts are recorded at {bank}.",
    "bal_by": "Balances by {dim} (total {total}):", "dim_currency": "currency", "dim_type": "account type", "dim_account": "account",
    "ef_no_expenses": "No expenses are recorded yet, so months of emergency-fund coverage cannot be measured.",
    "ef_head": "Your emergency fund covers {months} months of expenses.",
    "ef_liquid": "Liquid money (cash and certificates, gold not included): {amount}.",
    "ef_avg": "Average monthly expenses: {amount} (average of the {n} month(s) with expenses in the last 180 days).",
    "ef_target": "Target of {target} months = {amount}: {status}",
    "ef_met": "met ({ratio} times the target).", "ef_short": "not met, short by {gap}.",
    "cert_none": "No active certificates are recorded.",
    "cert_sum": "{n} active certificate(s): principal {principal}, monthly interest {interest}, weighted rate {rate}%.",
    "cert_list": "Active certificates ({n}), amounts in {cur}:", "cert_next": "Next interest posting: {value} at {bank} on {date}.",
    "cert_next_none": "No upcoming interest posting is scheduled.", "cert_mat": "Nearest maturity: {bank}, {amount} on {date} ({days} days).",
    "cert_mat_none": "No certificate expiry dates are recorded.",
    "as_none": "No fixed assets are recorded.", "as_total": "Total fixed assets: {amount} across {n} asset(s).",
    "as_by": "Fixed assets by type (total {total}):", "as_list": "Fixed assets ({n}), values in {cur}:",
    "as_type": "{type} assets: {amount} across {n} asset(s).", "as_type_none": "No {type} assets are recorded.",
    "gold_none": "No gold price has been fetched yet.", "gold_one": "Gold {k}K price per gram: sell {sell}, buy {buy} (updated {when}).",
    "gold_side": "Gold {k}K {side} price per gram: {price} (updated {when}).", "gold_all": "Gold prices per gram in {cur} (updated {when}):",
    "gold_oz": "Gold ounce price: {usd} USD (≈ {usd_g} USD per gram 24K, updated {when}).", "side_sell": "sell", "side_buy": "buy",
    "gold_bad_karat": "Gold prices are stored for 24K, 22K, 21K and 18K only.",
    "fx_none": "No exchange rate is stored for {code}.", "fx_one": "1 {code} = {mid} {home} (buy {buy}, sell {sell}; updated {when}).",
    "fx_side": "1 {code} = {price} {home} ({side}; updated {when}).", "fx_all": "Exchange rates against {home} (updated {when}):",
    "fx_empty": "No exchange rates are stored yet.", "side_mid": "mid",
    "gh_none": "No gold holdings are recorded.", "gh_total": "Gold holdings: {grams} g in total, worth {value}.",
    "gh_by": "Gold holdings by source (amounts in {cur}):", "col_source": "Source", "col_purity": "Purity", "col_grams": "Grams",
    "src_balance": "Balance", "src_asset": "Fixed asset (not in Balance)",
    "gh_synced": "Includes {n} gold fixed asset(s) ({grams} g): they are synced into your Balance gold entries and counted once.",
    "only_current": "I can only show the current state of budgets and recurring items, not a past month.", "bud_none": "No active budgets are set.", "bud_none_cat": "No active budget is set for {cat}.",
    "bud_all_cats": "All categories", "bud_status": "Budget status: {n} active budget(s), amounts in {cur}.",
    "bud_over": "Budgets over the limit: {over}; close to the alert level: {near} (amounts in {cur}).",
    "bud_all_ok": "All {n} budget(s) are within their limits.", "bud_remaining": "Left across the shown budgets (amounts in {cur}): {amount}.",
    "per_weekly": "Weekly", "per_monthly": "Monthly", "per_yearly": "Yearly",
    "col_period": "Period", "col_limit": "Limit", "col_spent": "Spent", "col_left": "Left", "col_used": "Used",
    "rec_none": "No active recurring transactions are set.", "rec_none_upcoming": "Nothing recurring is due in the next {days} days.",
    "rec_list": "Active recurring transactions ({n}):", "rec_upcoming": "{n} recurring item(s) due in the next {days} days:",
    "rec_total": "Recurring commitments come to about {amount} per month across {n} item(s).",
    "rec_skipped": "{n} item(s) were left out because no exchange rate is stored for their currency.",
    "freq_daily": "Every {n} day(s)", "freq_weekly": "Every {n} week(s)", "freq_monthly": "Every {n} month(s)", "freq_yearly": "Every {n} year(s)",
    "col_frequency": "Repeats", "col_next_due": "Next due",
}
_EN.update({
    "wf_empty": "There is not enough data for a net worth forecast yet (no balances, certificates, gold, assets or salary records).",
    "wf_head_date": "Net worth forecast for {target} (amounts in {cur}, as of {as_of}):",
    "wf_head_now": "Net worth forecast (amounts in {cur}, as of {as_of}):",
    "wf_col_item": "Component",
    "wf_col_now": "Now",
    "wf_col_forecast": "Forecast",
    "wf_sc_conservative": "Conservative",
    "wf_sc_expected": "Expected",
    "wf_sc_optimistic": "Optimistic",
    "wf_liquid": "Liquid cash",
    "wf_certs": "Bank certificates",
    "wf_gold": "Gold",
    "wf_fixed": "Fixed assets",
    "wf_net": "Net worth",
    "wf_change": "Change",
    "wf_note_month_end": "The model projects month-end values, so {target} is shown as {used}.",
    "wf_note_beyond": "The forecast model reaches {last}; that date is shown instead of {target}.",
    "wf_note_past": "{target} is not in the future, so today's values are shown.",
    "wf_monthly": "Expected monthly increase: {amount} (largest driver: {driver}).",
    "wf_drv_salary": "salary",
    "wf_drv_rental_income": "rental income",
    "wf_drv_asset_sale": "asset sales",
    "wf_drv_gold": "gold",
    "wf_drv_certificates": "certificate interest",
    "wf_drv_fixed_assets": "fixed assets",
    "wf_drv_none": "none",
})
_TABLES = {"en": _EN, "ar": _AR, "fr": labels_fr.TABLE, "de": labels_de.TABLE}


def t(lang: str, key: str, **kw) -> str:
    table = _TABLES.get(lang) or _EN
    return (table.get(key) or _EN[key]).format(**kw)


def month_label(lang: str, year: int, month: int, abbr: bool = False) -> str:
    if lang == "ar":
        return f"{_AR_MONTHS[month - 1]} {year}"
    if lang in ("fr", "de"):
        mod = labels_fr if lang == "fr" else labels_de
        return f"{(mod.MONTHS_ABBR if abbr else mod.MONTHS)[month - 1]} {year}"
    return f"{(calendar.month_abbr if abbr else calendar.month_name)[month]} {year}"


def range_label(lang: str, periods: list[tuple[int, int]]) -> str:
    """One month -> 'September 2026'; a run -> 'Jun 2026 – Sep 2026'; scattered -> 'Jun 2026, Aug 2026'."""
    if not periods:
        return ""
    if len(periods) == 1:
        return month_label(lang, *periods[0])
    idx = [y * 12 + m for y, m in periods]
    if idx == list(range(idx[0], idx[0] + len(idx))):
        return f"{month_label(lang, *periods[0], abbr=True)} – {month_label(lang, *periods[-1], abbr=True)}"
    return ", ".join(month_label(lang, y, m, abbr=True) for y, m in periods)
