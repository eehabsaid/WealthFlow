# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

from django.http import JsonResponse
from django.views import View

from core.validators import _api_auth_required
from core.validators.json_body import parse_json_body


class ImportPreviewView(View):
    """POST multipart/form-data: file=<csv or xlsx>. Returns parsed
    headers, a suggested column mapping, a sample for display, and every
    parsed row (the client resends these rows verbatim to /confirm/)."""

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return JsonResponse({"error": "No file uploaded", "error_key": "no_file"}, status=400)

        from core.services.import_data import ImportService
        from core.services.import_data.parsers import EmptyFileError, UnsupportedFileTypeError

        try:
            preview = ImportService.preview(uploaded_file)
        except UnsupportedFileTypeError:
            return JsonResponse(
                {"error": "Unsupported file type — upload a .csv or .xlsx file", "error_key": "unsupported_file_type"},
                status=400,
            )
        except EmptyFileError:
            return JsonResponse({"error": "The file has no rows", "error_key": "empty_file"}, status=400)
        return JsonResponse(preview)


class ImportConfirmView(View):
    """POST JSON: {mapping, rows, currency_id, category_id, payment_method,
    skip_duplicates}. `rows` is exactly what /preview/ returned as
    `rows` (or a user-edited subset of it)."""

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        data = parse_json_body(request)
        rows = data.get("rows")
        mapping = data.get("mapping")
        if not isinstance(rows, list) or not rows:
            return JsonResponse({"error": "No rows to import", "error_key": "no_rows"}, status=400)
        if not isinstance(mapping, dict) or not mapping.get("date") or not mapping.get("amount"):
            return JsonResponse(
                {"error": "Date and amount columns must be mapped", "error_key": "mapping_incomplete"},
                status=400,
            )

        from core.services.import_data import ImportService

        result = ImportService.confirm(
            request.user,
            rows,
            mapping,
            currency_id=data.get("currency_id"),
            category_id=data.get("category_id"),
            payment_method=data.get("payment_method", "Cash"),
            skip_duplicates=data.get("skip_duplicates", True),
        )
        return JsonResponse(result)
