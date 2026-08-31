"""
data_phase.py
=============
NOTE: Part of the generate_report_generator package split (see package
__init__.py docstring). Owns the pre-PDF data phase: resolving the period
(monthly/yearly/custom), filtering expenses, and computing income/expense/
interest/savings aggregates plus the category breakdown.
"""
import datetime

from core.models import Expense, BankCertificate
from core.reports.report_utils import format_arabic


def resolve_period(data, t):
    """Returns (rtype, year, month, start_date, end_date, title_str, filename, qs)."""
    rtype = data.get("type", "monthly")
    year = int(data.get("year", datetime.date.today().year))
    month = int(data.get("month", datetime.date.today().month))

    # Accept both parameter styles (with or without suffix) to be fully secure
    start_date = data.get("start_date") or data.get("start")
    end_date = data.get("end_date") or data.get("end")

    qs = Expense.objects.select_related("category", "subcategory").all()
    if rtype == "monthly":
        qs = qs.filter(year=year, month=month)
        json_month_key = f"month_short_{month}"
        translated_month = t.get(json_month_key) or t.get(
            f"month_{datetime.date(year, month, 1).strftime('%B').lower()}",
            datetime.date(year, month, 1).strftime("%B"),
        )
        title_str = f"{t.get('monthly_report', 'Monthly Report')} - {translated_month} {year}"
        filename = f"report_{year}_{month:02d}.pdf"
    elif rtype == "yearly":
        qs = qs.filter(year=year)
        title_str = f"{t.get('yearly_report', 'Yearly Report')} - {year}"
        filename = f"report_{year}.pdf"
    else:
        from datetime import date as _date

        sd = _date.fromisoformat(start_date)
        ed = _date.fromisoformat(end_date)
        qs = qs.filter(date__gte=sd, date__lte=ed)

        title_str = f"{t.get('report', 'Report')} {start_date} {t.get('to', 'to')} {end_date}"
        filename = f"report_{start_date}_{end_date}.pdf"

    return rtype, year, month, start_date, end_date, title_str, filename, qs


def build_report_data(data, lang, t):
    """Resolves the period, filters expenses, and computes all aggregates.

    Returns a dict of the fields required to construct a ReportContext.
    """
    rtype, year, month, start_date, end_date, title_str, filename, qs = resolve_period(data, t)

    if lang == "ar":
        title_str = format_arabic(title_str)

    expenses = list(qs)
    total_exp = sum(float(e.amount_egp) for e in expenses)

    # Income for period (salary paid amounts)
    from core.services.reports.report_service import ReportService

    total_inc = ReportService.get_period_income(rtype, year, month, start_date, end_date)

    # Add bank interest (summing all certificates)
    total_interest = sum(float(c.interest_value or 0) for c in BankCertificate.objects.all())
    total_inc += total_interest

    net_sav = total_inc - total_exp
    sav_rate = (net_sav / total_inc * 100) if total_inc > 0 else 0

    cat_totals = {}
    for e in expenses:
        cname = e.category.name if e.category else "Uncategorised"
        cat_totals[cname] = cat_totals.get(cname, 0) + float(e.amount_egp)

    return {
        "rtype": rtype,
        "year": year,
        "month": month,
        "start_date": start_date,
        "end_date": end_date,
        "title_str": title_str,
        "filename": filename,
        "expenses": expenses,
        "total_exp": total_exp,
        "total_inc": total_inc,
        "net_sav": net_sav,
        "sav_rate": sav_rate,
        "cat_totals": cat_totals,
    }
