# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Sum, Count, Q
from core.models import SalaryEntry, Company

@method_decorator(csrf_exempt, name="dispatch")
class SalaryReportView(View):
    """Salary + bonus analytics by year and company."""

    def get(self, request):

        year = request.GET.get("year")
        company_id = request.GET.get("company_id")

        qs = SalaryEntry.objects.all()
        if year:
            qs = qs.filter(year=int(year))
        if company_id:
            qs = qs.filter(company_id=int(company_id))

        # By year
        by_year = list(
            qs.values("year")
            .annotate(
                total_paid=Sum("paid"),
                total_bonus=Sum("bonus"),
                total_expected=Sum("expected"),
                paid_months=Count("id", filter=Q(paid__gt=0)),
            )
            .order_by("year")
        )

        # By company
        by_company = []
        for c in Company.objects.all().order_by("order"):
            cqs = qs.filter(company=c)
            agg = cqs.aggregate(
                total_paid=Sum("paid"),
                total_bonus=Sum("bonus"),
                total_expected=Sum("expected"),
                paid_months=Count("id", filter=Q(paid__gt=0)),
            )
            if agg["paid_months"]:
                by_company.append(
                    {
                        "company_id": c.id,
                        "company_name": c.display_name or c.name,
                        "color_hex": c.color_hex,
                        "total_paid": float(agg["total_paid"] or 0),
                        "total_bonus": float(agg["total_bonus"] or 0),
                        "total_expected": float(agg["total_expected"] or 0),
                        "paid_months": agg["paid_months"] or 0,
                    }
                )

        # Grand totals
        grand = qs.aggregate(
            total_paid=Sum("paid"),
            total_bonus=Sum("bonus"),
            total_expected=Sum("expected"),
            paid_months=Count("id", filter=Q(paid__gt=0)),
        )

        # Available years
        years = list(
            SalaryEntry.objects.values_list("year", flat=True)
            .distinct()
            .order_by("year")
        )
        companies = [
            {"id": c.id, "name": c.display_name or c.name}
            for c in Company.objects.all().order_by("order")
        ]

        return JsonResponse(
            {
                "by_year": by_year,
                "by_company": by_company,
                "grand": {
                    "total_paid": float(grand["total_paid"] or 0),
                    "total_bonus": float(grand["total_bonus"] or 0),
                    "total_expected": float(grand["total_expected"] or 0),
                    "paid_months": grand["paid_months"] or 0,
                },
                "years": years,
                "companies": companies,
            }
        )
