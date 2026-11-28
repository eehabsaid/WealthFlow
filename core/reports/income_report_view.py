from django.views import View
from django.http import JsonResponse
from core.validators import _api_auth_required
from core.services.reports.income_analytics import build_income_analytics


class IncomeReportView(View):
    """Income Analytics: every income source, off / yoy / mom compare modes (read-only)."""

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            data = build_income_analytics(request.user, request.GET)
        except (ValueError, TypeError) as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse(data)


class IncomeExportView(View):
    """Income Analytics export: ?format=xlsx|pdf with the same params as the API."""

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        fmt = request.GET.get("format")
        if fmt not in ("xlsx", "pdf"):
            return JsonResponse({"error": "format must be xlsx or pdf"}, status=400)
        from core.reports.income_export import income_excel_response, income_pdf_response

        try:
            if fmt == "xlsx":
                return income_excel_response(request.user, request.GET)
            return income_pdf_response(request.user, request.GET)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
