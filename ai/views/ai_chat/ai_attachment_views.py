"""Upload a file for the next chat message. Owner-scoped; the file is read by code (no model) and stored until the message is sent."""

from django.http import HttpResponse, JsonResponse
from django.views import View

from ai.models.ai_attachment import AIAttachment
from ai.services.attachments import AttachmentError, save_upload
from ai.services.attachments.extract import MAX_BYTES
from ai.views.ai_chat.ai_chat_helpers import _api_auth_required

REASONS = {"unsupported_type": "File type not supported.", "too_large": "File is larger than 10 MB.",
           "unreadable": "The file could not be read.", "empty": "The file has no readable text."}


class AIAttachmentUploadView(View):
    """POST /api/financial-advisor/ai/attachments/  (multipart field `file`) -> {attachment: {id, name, kind, size}}"""

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        upload = request.FILES.get("file")
        if upload is None:
            return JsonResponse({"error": "file_required"}, status=400)
        if upload.size > MAX_BYTES:
            return JsonResponse({"error": "too_large", "message": REASONS["too_large"]}, status=413)
        try:
            item = save_upload(request.user, upload.name, upload.read())
        except AttachmentError as exc:
            return JsonResponse({"error": str(exc), "message": REASONS.get(str(exc), "Upload failed.")}, status=400)
        return JsonResponse({"attachment": item.to_dict()}, status=201)


class AIAttachmentDetailView(View):
    """DELETE removes an unsent attachment; GET (pictures) shows it again in the chat history."""

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        gone, _ = AIAttachment.objects.filter(user=request.user, pk=pk, message__isnull=True).delete()
        return JsonResponse({"ok": bool(gone)}, status=200 if gone else 404)

    def get(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        item = AIAttachment.objects.filter(user=request.user, pk=pk, kind="image").first()
        if item is None:
            return JsonResponse({"error": "not_found"}, status=404)
        response = HttpResponse(bytes(item.data or b""), content_type=item.mime or "application/octet-stream")
        response["X-Content-Type-Options"] = "nosniff"
        safe = "".join(c for c in item.name if c.isprintable() and c not in '"\\')
        if request.GET.get("download"):   # the Download button: the file is saved instead of shown
            response["Content-Disposition"] = f'attachment; filename="{safe}"'
        else:
            response["Content-Disposition"] = "inline"
        return response
