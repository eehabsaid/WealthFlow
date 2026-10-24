"""GET /api/financial-advisor/ai/messages/<id>/export/<format>/ -> that assistant answer as a file.

Owner-scoped: only the conversation's own user can download; any other id answers 404 (never 403, so ids
do not leak). The file is built from the saved answer text, so it always equals what the chat showed."""

import logging

from django.http import HttpResponse, JsonResponse
from django.views import View

from core.models import AIMessage
from core.services.ai.exports import build_file, get_format
from core.services.ai.exports.settings import get_settings
from core.views.ai_chat.ai_chat_helpers import _api_auth_required


logger = logging.getLogger(__name__)


class AIMessageExportView(View):
    def get(self, request, pk, fmt):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        cfg = get_settings()
        if not cfg.enabled:
            return JsonResponse({"error": "disabled", "detail": "File generation is switched off in Settings > AI Advisor."}, status=404)
        export_format = get_format(fmt)
        message = (AIMessage.objects.select_related("conversation")
                   .filter(pk=pk, role="assistant", is_deleted=False, conversation__user=request.user, conversation__is_deleted=False).first())
        if export_format is None or message is None:
            return JsonResponse({"error": "not_found"}, status=404)
        from core.views.ai_chat.ai_chat_core_views.response_finalizer import is_non_answer

        if is_non_answer(message.content):   # a refusal is not a document: never turn it into a file
            return JsonResponse({"error": "no_content"}, status=404)
        content, filename = build_file(message, export_format)
        if len(content) > cfg.max_bytes:
            return JsonResponse({"error": "too_large", "detail": f"The file would be {len(content) // 1024} KB; the limit is {cfg.max_bytes // 1024 // 1024} MB."}, status=413)
        response = HttpResponse(content, content_type=export_format.mime)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        _audit(request.user, f"{filename} ({export_format.key}, {len(content)} bytes, message {message.id})")
        return response


def _audit(user, details: str) -> None:
    try:
        from core.authentication.utils.auth_utils import record_audit

        record_audit(user, "ai_file_downloaded", actor=user, details=details[:500])
    except Exception:   # an audit hiccup must never block the user's own file
        logger.warning("could not write the ai_file_downloaded audit entry", exc_info=True)
