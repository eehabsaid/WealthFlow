# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import datetime
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Sum
from core.models import SalaryEntry, Expense, BankCertificate
from core.services.balance.financial_sync_service import FinancialSyncService


@method_decorator(csrf_exempt, name="dispatch")
class ExpenseSummaryView(View):
    """Returns monthly totals + category breakdown for charts."""

    def get(self, request):
        import calendar

        year = request.GET.get("year")
        month = request.GET.get("month")
        qs = Expense.objects.all()
        if year:
            qs = qs.filter(year=int(year))
        if month:
            qs = qs.filter(month=int(month))

        # By category
        by_cat = {}
        for e in qs.select_related("category"):
            name = e.category.name if e.category else "Uncategorised"
            icon = e.category.icon if e.category else "💰"
            color = e.category.color_hex if e.category else "#6c757d"
            key = name
            if key not in by_cat:
                by_cat[key] = {"name": name, "icon": icon, "color": color, "total": 0}
            by_cat[key]["total"] += float(e.amount_egp)

        # Monthly trend (last 12 months)
        monthly = []
        for m in range(1, 13):
            y = int(year) if year else datetime.date.today().year
            total = (
                Expense.objects.filter(year=y, month=m).aggregate(t=Sum("amount_egp"))["t"]
                or 0
            )
            monthly.append({"month": m, "total": float(total)})

        grand_total = sum(v["total"] for v in by_cat.values())

        # Income summary for reports (salary + certificate interest)
        month_names = [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ]

        def _month_bounds(y, m):
            start = datetime.date(y, m, 1)
            end = datetime.date(y, m, calendar.monthrange(y, m)[1])
            return start, end

        def _year_bounds(y):
            return datetime.date(y, 1, 1), datetime.date(y, 12, 31)

        def _includes_in_period(certificate, start_date, end_date):
            if not certificate:
                return False
            issue_date = certificate.issue_date
            expiry_date = certificate.expiry_date
            if issue_date and issue_date > end_date:
                return False
            if expiry_date and expiry_date < start_date:
                return False
            return True

        salary_amount = 0.0
        total_interest = 0.0
        rental_income = 0.0

        if month:
            target_year = int(year) if year else datetime.date.today().year
            target_month = int(month)
            prev_month = target_month - 1
            prev_year = target_year
            if prev_month == 0:
                prev_month = 12
                prev_year -= 1

            prev_month_name = month_names[prev_month - 1]
            salary_qs = SalaryEntry.objects.filter(
                year=prev_year,
                month__iexact=prev_month_name,
            )
            salary_amount = float(
                salary_qs.aggregate(total=Sum("paid"))["total"] or 0
            )

            start_date, end_date = _month_bounds(target_year, target_month)
            certs = BankCertificate.objects.all()
            total_interest = sum(
                float(c.interest_value or 0)
                for c in certs
                if _includes_in_period(c, start_date, end_date)
            )
            rental_income = float(FinancialSyncService().period_rental_income_total("month"))
        elif year:
            salary_amount = float(
                SalaryEntry.objects.filter(year=int(year)).aggregate(total=Sum("paid"))["total"]
                or 0
            )
            start_date, end_date = _year_bounds(int(year))
            certs = BankCertificate.objects.all()
            total_interest = sum(
                float(c.interest_value or 0)
                for c in certs
                if _includes_in_period(c, start_date, end_date)
            )
            rental_income = float(FinancialSyncService().period_rental_income_total("year"))
        else:
            today = datetime.date.today()
            start_date, end_date = _month_bounds(today.year, today.month)
            salary_amount = 0.0
            total_interest = sum(
                float(c.interest_value or 0)
                for c in BankCertificate.objects.all()
                if _includes_in_period(c, start_date, end_date)
            )
            rental_income = float(FinancialSyncService().period_rental_income_total("month"))

        total_income = salary_amount + total_interest + rental_income

        return JsonResponse(
            {
                "by_category": list(by_cat.values()),
                "monthly_trend": monthly,
                "grand_total": grand_total,
                "income_summary": {
                    "total_income": total_income,
                    "total_salary": salary_amount,
                    "total_interest": total_interest,
                    "total_rental_income": rental_income,
                },
            }
        )
