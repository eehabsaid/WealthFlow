# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import datetime
from django.http import JsonResponse
from django.views import View
from django.db.models import Sum
from core.models import Expense
from core.services.reports.income_summary_service import build_income_summary
from core.validators import _api_auth_required


class ExpenseSummaryView(View):
    """Returns monthly totals + category breakdown for charts."""

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        owner = request.user
        year = request.GET.get("year")
        month = request.GET.get("month")
        qs = Expense.objects.filter(owner=owner)
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
            by_cat[key]["total"] += float(e.amount_base)

        # Monthly trend (last 12 months)
        monthly = []
        for m in range(1, 13):
            y = int(year) if year else datetime.date.today().year
            total = (
                Expense.objects.filter(owner=owner, year=y, month=m).aggregate(t=Sum("amount_base"))["t"]
                or 0
            )
            monthly.append({"month": m, "total": float(total)})

        grand_total = sum(v["total"] for v in by_cat.values())

        start, end = request.GET.get("start"), request.GET.get("end")
        try:
            start = datetime.date.fromisoformat(start) if start else None
            end = datetime.date.fromisoformat(end) if end else None
        except ValueError:
            return JsonResponse({"error": "start and end must be YYYY-MM-DD"}, status=400)
        income_summary = build_income_summary(
            owner, int(year) if year else None, int(month) if month else None, start, end
        )

        return JsonResponse(
            {
                "by_category": list(by_cat.values()),
                "monthly_trend": monthly,
                "grand_total": grand_total,
                "income_summary": income_summary,
            }
        )
