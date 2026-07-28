# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Sum, Count
from core.models import BankCertificate
from datetime import date, timedelta

@method_decorator(csrf_exempt, name="dispatch")
class CertificateReportView(View):
    """Certificate maturity and analytics report."""

    def get(self, request):

        today = date.today()
        active_certs = BankCertificate.objects.select_related("bank", "currency").filter(
            status__iexact="active"
        )

        agg = active_certs.aggregate(
            total_count=Count("id"),
            total_amount=Sum("amount"),
            total_interest=Sum("interest_value"),
        )

        # Maturity buckets (configurable label from settings, days from AppSettings)
        bucket_days = [
            ("overdue", 0, -1),
            ("30_days", 0, 30),
            ("90_days", 31, 90),
            ("180_days", 91, 180),
            ("later", 181, 9999),
        ]

        buckets = {}
        for label, low, high in bucket_days:
            if label == "overdue":
                buckets[label] = [
                    c.to_dict()
                    for c in active_certs.filter(expiry_date__lt=today)
                ]
            else:
                buckets[label] = [
                    c.to_dict()
                    for c in active_certs.filter(
                        expiry_date__gte=today + timedelta(days=low),
                        expiry_date__lte=today + timedelta(days=high),
                    )
                ]

        # By status (active certificates only)
        by_status = {}
        for c in active_certs:
            by_status[c.status] = by_status.get(c.status, {"count": 0, "total": 0})
            by_status[c.status]["count"] += 1
            by_status[c.status]["total"] += float(c.amount)

        # Monthly interest cashflow (next 12 months) for active certificates only
        monthly_cf = []
        for i in range(12):
            m_start = today.replace(day=1) + timedelta(days=32 * i)
            m_start = m_start.replace(day=1)
            m_certs = active_certs.filter(
                expiry_date__year=m_start.year,
                expiry_date__month=m_start.month,
            )
            monthly_cf.append(
                {
                    "month": m_start.strftime("%b %Y"),
                    "count": m_certs.count(),
                    "amount": float(m_certs.aggregate(s=Sum("amount"))["s"] or 0),
                }
            )

        total_interest = float(agg["total_interest"] or 0)
        monthly_interest = (total_interest) if total_interest else 0.0

        return JsonResponse(
            {
                "summary": {
                    "total_count": agg["total_count"] or 0,
                    "total_amount": float(agg["total_amount"] or 0),
                    "total_interest": total_interest,
                    "monthly_interest": monthly_interest,
                },
                "buckets": buckets,
                "by_status": by_status,
                "monthly_cf": monthly_cf,
            }
        )
