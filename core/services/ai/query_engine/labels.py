"""en / ar wording for every answer the engine writes. Code-generated text only: no LLM."""

from __future__ import annotations

import calendar

_AR_MONTHS = ("يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر")

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
    "bal_total": "Total balance: {amount} across {n} account(s).", "bal_gold": "Gold holdings: {grams} g, worth {amount}.",
    "bal_gold_note": "Gold is included in the total ({amount}).", "bal_none": "No balance accounts are recorded.",
    "bal_cur": "Balance in {cur}: {amount} across {n} account(s) (≈ {home}).", "bal_cur_none": "No {cur} balance is recorded.",
    "bal_bank": "Balance at {bank}: {home} across {n} account(s).", "bal_bank_none": "No accounts are recorded at {bank}.",
    "bal_by": "Balances by {dim} (total {total}):", "dim_currency": "currency", "dim_type": "account type", "dim_account": "account",
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
}
_AR = {
    "uncategorized": "بدون تصنيف", "no_date": "بدون تاريخ", "grand": "الإجمالي الكلي", "total_of": "إجمالي {label}",
    "col_date": "التاريخ", "col_total": "الإجمالي", "col_details": "التفاصيل", "col_category": "الفئة", "col_share": "النسبة",
    "col_tx": "المعاملات", "col_month": "الشهر", "col_desc": "الوصف", "col_amount": "المبلغ",
    "col_company": "الشركة", "col_expected": "المتوقع", "col_paid": "المدفوع", "col_bonus": "المكافأة",
    "col_account": "الحساب", "col_type": "النوع", "col_bank": "البنك", "col_currency": "العملة", "col_balance": "الرصيد",
    "col_home": "بـ {cur}", "col_rate": "المعدل", "col_expiry": "الاستحقاق", "col_principal": "أصل المبلغ",
    "col_interest": "العائد الشهري", "col_value": "القيمة", "col_karat": "العيار", "col_sell": "بيع", "col_buy": "شراء",
    "col_mid": "المتوسط", "col_name": "الاسم", "col_days": "الأيام المتبقية", "col_next": "العائد القادم",
    "head_tx": "{amount} عبر {n} معاملة", "exp_none": "لا توجد مصروفات مسجلة لـ {label}.",
    "exp_total": "إجمالي المصروفات لـ {label}: {head}.", "exp_total_cat": "إجمالي المصروفات لـ {label} في {cat}: {head}.",
    "exp_daily": "المصروفات اليومية لـ {label} (الإجمالي {head}):", "exp_cat": "المصروفات حسب الفئة لـ {label} (الإجمالي {head}):",
    "exp_month": "المصروفات حسب الشهر لـ {label} (الإجمالي {head}، المبالغ بـ {cur}):",
    "exp_table": "المصروفات لـ {label} ({n} معاملة، المبالغ بـ {cur}):", "exp_empty_note": "لا توجد مصروفات مسجلة لـ: {labels}.",
    "exp_latest": "آخر {n} مصروف (المبالغ بـ {cur}):", "exp_top": "أكبر {n} مصروف لـ {label} (المبالغ بـ {cur}):",
    "exp_avg": "متوسط المصروفات الشهرية لـ {label}: {amount} (على {n} شهر بها بيانات).",
    "exp_top_cat": "أعلى فئة إنفاق لـ {label}: {name} — {amount} ({share}).",
    "exp_capped": "يتم عرض أول {shown} من {n} معاملة؛ الإجماليات تشمل الكل.",
    "sal_none": "لا يوجد راتب مسجل لـ {label}.", "sal_month": "الراتب المدفوع لـ {label}: {parts}.",
    "sal_part": "{amount} من {company}", "sal_latest": "آخر راتب مدفوع: {amount} عن {month} {year} من {company}.",
    "sal_none_any": "لا توجد رواتب مسجلة.", "sal_table": "الراتب لـ {label} (المبالغ بـ {cur}):",
    "sal_total": "إجمالي {what} لـ {label}: {amount}.", "sal_avg": "متوسط {what} الشهري لـ {label}: {amount} (على {n} شهر).",
    "what_paid": "الراتب المدفوع", "what_expected": "الراتب المتوقع", "what_bonus": "المكافآت",
    "bal_total": "إجمالي الرصيد: {amount} في {n} حساب.", "bal_gold": "الذهب: {grams} جم بقيمة {amount}.",
    "bal_gold_note": "الذهب محسوب ضمن الإجمالي ({amount}).", "bal_none": "لا توجد حسابات رصيد مسجلة.",
    "bal_cur": "الرصيد بعملة {cur}: {amount} في {n} حساب (≈ {home}).", "bal_cur_none": "لا يوجد رصيد بعملة {cur}.",
    "bal_bank": "الرصيد في {bank}: {home} في {n} حساب.", "bal_bank_none": "لا توجد حسابات مسجلة في {bank}.",
    "bal_by": "الأرصدة حسب {dim} (الإجمالي {total}):", "dim_currency": "العملة", "dim_type": "نوع الحساب", "dim_account": "الحساب",
    "cert_none": "لا توجد شهادات نشطة مسجلة.",
    "cert_sum": "{n} شهادة نشطة: أصل المبلغ {principal}، العائد الشهري {interest}، متوسط المعدل {rate}%.",
    "cert_list": "الشهادات النشطة ({n})، المبالغ بـ {cur}:", "cert_next": "أقرب صرف عائد: {value} في {bank} بتاريخ {date}.",
    "cert_next_none": "لا يوجد صرف عائد قادم مجدول.", "cert_mat": "أقرب استحقاق: {bank}، {amount} بتاريخ {date} (بعد {days} يوم).",
    "cert_mat_none": "لا توجد تواريخ استحقاق مسجلة للشهادات.",
    "as_none": "لا توجد أصول ثابتة مسجلة.", "as_total": "إجمالي الأصول الثابتة: {amount} في {n} أصل.",
    "as_by": "الأصول الثابتة حسب النوع (الإجمالي {total}):", "as_list": "الأصول الثابتة ({n})، القيم بـ {cur}:",
    "as_type": "أصول {type}: {amount} في {n} أصل.", "as_type_none": "لا توجد أصول من نوع {type}.",
    "gold_none": "لم يتم جلب سعر الذهب بعد.", "gold_one": "سعر جرام الذهب عيار {k}: بيع {sell}، شراء {buy} (آخر تحديث {when}).",
    "gold_side": "سعر {side} جرام الذهب عيار {k}: {price} (آخر تحديث {when}).", "gold_all": "أسعار جرام الذهب بـ {cur} (آخر تحديث {when}):",
    "gold_oz": "سعر أونصة الذهب: {usd} دولار (≈ {usd_g} دولار لجرام عيار 24، آخر تحديث {when}).", "side_sell": "البيع", "side_buy": "الشراء",
    "gold_bad_karat": "أسعار الذهب متاحة لعيار 24 و22 و21 و18 فقط.",
    "fx_none": "لا يوجد سعر صرف مسجل لـ {code}.", "fx_one": "1 {code} = {mid} {home} (شراء {buy}، بيع {sell}؛ آخر تحديث {when}).",
    "fx_side": "1 {code} = {price} {home} ({side}؛ آخر تحديث {when}).", "fx_all": "أسعار الصرف مقابل {home} (آخر تحديث {when}):",
    "fx_empty": "لا توجد أسعار صرف مسجلة بعد.", "side_mid": "المتوسط",
    "gh_none": "لا توجد مقتنيات ذهب مسجلة.", "gh_total": "مقتنيات الذهب: {grams} جم إجمالاً بقيمة {value}.",
    "gh_by": "مقتنيات الذهب حسب المصدر (المبالغ بـ {cur}):", "col_source": "المصدر", "col_purity": "العيار", "col_grams": "الجرامات",
    "src_balance": "الرصيد", "src_asset": "أصل ثابت (غير مضاف للرصيد)",
    "gh_synced": "يشمل {n} أصل ذهب ثابت ({grams} جم): تتم مزامنتها مع أرصدة الذهب في الرصيد وتُحسب مرة واحدة.",
}
_TABLES = {"en": _EN, "ar": _AR}


def t(lang: str, key: str, **kw) -> str:
    table = _TABLES.get(lang) or _EN
    return (table.get(key) or _EN[key]).format(**kw)


def month_label(lang: str, year: int, month: int, abbr: bool = False) -> str:
    if lang == "ar":
        return f"{_AR_MONTHS[month - 1]} {year}"
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
