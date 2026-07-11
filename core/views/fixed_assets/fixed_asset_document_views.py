# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.utils import OperationalError, ProgrammingError
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from core.services.shared.document_service import DocumentService

def _document_validation_error_response(exc):
    if hasattr(exc, "messages") and exc.messages:
        message = str(exc.messages[0])
    else:
        message = str(exc)
    return JsonResponse({"error": message}, status=400)

def _document_database_error_response(exc):
    message = str(exc or "")
    if "no such table" in message.lower() and "core_document" in message.lower():
        return JsonResponse(
            {"error": "documents_schema_missing", "detail": "Run database migrations to enable document management."},
            status=503,
        )
    return JsonResponse({"error": "documents_unavailable"}, status=503)

@method_decorator(csrf_exempt, name="dispatch")
class DocumentListUploadView(View):
    service = DocumentService()

    def get(self, request, parent_type, parent_id):
        try:
            docs = self.service.list_documents(parent_type, parent_id)
            return JsonResponse({"documents": docs})
        except ValidationError as exc:
            return _document_validation_error_response(exc)
        except (OperationalError, ProgrammingError) as exc:
            return _document_database_error_response(exc)

    def post(self, request, parent_type, parent_id):
        uploaded_file = request.FILES.get("file")
        category = request.POST.get("document_category")
        notes = request.POST.get("notes", "")

        try:
            item = self.service.upload_document(
                parent_type=parent_type,
                parent_id=parent_id,
                uploaded_file=uploaded_file,
                uploaded_by=request.user,
                category=category,
                notes=notes,
            )
            return JsonResponse(item, status=201)
        except ValidationError as exc:
            return _document_validation_error_response(exc)
        except (OperationalError, ProgrammingError) as exc:
            return _document_database_error_response(exc)

@method_decorator(csrf_exempt, name="dispatch")
class DocumentFileView(View):
    service = DocumentService()

    def get(self, request, document_id):
        try:
            metadata, content = self.service.get_document_content(document_id)
        except (OperationalError, ProgrammingError) as exc:
            return _document_database_error_response(exc)
        if metadata is None:
            return JsonResponse({"error": "document_not_found"}, status=404)

        disposition = request.GET.get("disposition", "inline").strip().lower()
        if disposition not in {"inline", "attachment"}:
            disposition = "inline"

        response = HttpResponse(content, content_type=metadata.get("mime_type") or "application/octet-stream")
        response["Content-Disposition"] = f'{disposition}; filename="{metadata.get("original_file_name", "document")}"'
        response["Content-Length"] = str(metadata.get("file_size", len(content)))
        return response

    def put(self, request, document_id):
        doc = self.service.get_document(document_id)
        if doc is None:
            return JsonResponse({"error": "document_not_found"}, status=404)

        uploaded_file = request.FILES.get("file")
        category = request.POST.get("document_category") if "document_category" in request.POST else None
        notes = request.POST.get("notes") if "notes" in request.POST else None

        try:
            item = self.service.replace_document(
                document_id=document_id,
                uploaded_file=uploaded_file,
                uploaded_by=request.user,
                category=category,
                notes=notes,
            )
            return JsonResponse(item)
        except ValidationError as exc:
            return _document_validation_error_response(exc)
        except (OperationalError, ProgrammingError) as exc:
            return _document_database_error_response(exc)

    def post(self, request, document_id):
        return self.put(request, document_id)

    def delete(self, request, document_id):
        try:
            deleted = self.service.delete_document(document_id)
        except (OperationalError, ProgrammingError) as exc:
            return _document_database_error_response(exc)
        if not deleted:
            return JsonResponse({"error": "document_not_found"}, status=404)
        return JsonResponse({"deleted": True})

@method_decorator(csrf_exempt, name="dispatch")
class DocumentCategoriesView(View):
    service = DocumentService()

    def get(self, request):
        parent_type = request.GET.get("parent_type", "")
        try:
            categories = self.service.categories_for_parent(parent_type)
            return JsonResponse({"categories": categories})
        except ValidationError as exc:
            return _document_validation_error_response(exc)
        except (OperationalError, ProgrammingError) as exc:
            return _document_database_error_response(exc)

