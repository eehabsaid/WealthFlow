"""GET /api/financial-advisor/ai/messages/<id>/export/<format>/ -> that assistant answer as a file.

Owner-scoped: only the conversation's own user can download; any other id answers 404 (never 403, so ids
do not leak). The file is built from the saved answer text, so it always equals what the chat showed."""

from django.http import HttpResponse, JsonResponse
from django.views import View

from core.models import AIMessage
from core.services.ai.exports import build_file, get_format
from core.views.ai_chat.ai_chat_helpers import _api_auth_required


class AIMessageExportView(View):
    def get(self, request, pk, fmt):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        export_format = get_format(fmt)
        message = (AIMessage.objects.select_related("conversation")
                   .filter(pk=pk, role="assistant", is_deleted=False, conversation__user=request.user, conversation__is_deleted=False).first())
        if export_format is None or message is None:
            return JsonResponse({"error": "not_found"}, status=404)
        content, filename = build_file(message, export_format)
        response = HttpResponse(content, content_type=export_format.mime)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response
