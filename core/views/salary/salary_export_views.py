"""GET /api/salary/export/?years=2026[,2025]&lang=en -> the user's salary entries as .xlsx (owner-scoped, read-only)."""

from django.http import JsonResponse, HttpResponse
from django.views import View

from core.validators import _api_auth_required

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class SalaryExportView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        from core.reports.salary_list_excel import build_salary_workbook, parse_years

        years = parse_years(request.GET.get("years", ""))
        buf, count = build_salary_workbook(request.user, years, str(request.GET.get("lang", "en")).lower())
        if not count:
            return JsonResponse({"error": "No salary entries to export"}, status=404)
        name = "Salaries_" + ("_".join(str(y) for y in years) if years else "All") + ".xlsx"
        response = HttpResponse(buf.read(), content_type=_XLSX)
        response["Content-Disposition"] = f'attachment; filename="{name}"'
        return response
