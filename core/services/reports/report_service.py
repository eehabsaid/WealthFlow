import datetime
from django.db.models import Sum
from core.models import SalaryEntry, Expense

class ReportService(object):
    @staticmethod
    def get_period_income(rtype, year, month, start_date=None, end_date=None):
        total_inc = 0.0
        if rtype == "monthly":
            # Target the previous month relative to the report month
            curr_date = datetime.date(year, month, 1)
            prev_date = curr_date - datetime.timedelta(days=1)
            sal_qs = SalaryEntry.objects.filter(
                year=prev_date.year, month=prev_date.strftime("%B")
            )
        elif rtype == "yearly":
            sal_qs = SalaryEntry.objects.filter(year=year)
        else:
            from datetime import date as _date
            if not start_date or not end_date:
                return 0.0
            sd = _date.fromisoformat(start_date)
            ed = _date.fromisoformat(end_date)
            MONTHS = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ]
            sal_qs = SalaryEntry.objects.none()
            for year_num in range(sd.year, ed.year + 1):
                year_entries = SalaryEntry.objects.filter(year=year_num)
                for entry in year_entries:
                    try:
                        month_index = MONTHS.index(entry.month) + 1
                        entry_date = _date(year_num, month_index, 1)
                        if sd <= entry_date <= ed:
                            sal_qs |= SalaryEntry.objects.filter(pk=entry.pk)
                    except Exception:
                        pass

        total_inc = float(sal_qs.aggregate(t=Sum("paid"))["t"] or 0)
        return total_inc
