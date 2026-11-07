import datetime

from core.services.reports.income_summary_service import build_income_summary


class ReportService(object):
    @staticmethod
    def get_period_income(owner, rtype, year, month, start_date=None, end_date=None):
        """Total income for a report period: the same figure the Expenses Report card shows
        (salary + certificate interest + rental income + manual income)."""
        if rtype == "monthly":
            summary = build_income_summary(owner, year, month)
        elif rtype == "yearly":
            summary = build_income_summary(owner, year)
        else:
            if not start_date or not end_date:
                return 0.0
            summary = build_income_summary(
                owner,
                start=datetime.date.fromisoformat(str(start_date)),
                end=datetime.date.fromisoformat(str(end_date)),
            )
        return summary["total_income"]
