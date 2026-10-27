from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.views import View

from core.models import AIMemoryNote
from core.services.ai.memory.store import BODY_MAX, TITLE_MAX
from core.validators.json_body import parse_json_body
from core.views.ai_chat.ai_chat_helpers import _api_auth_required


class AIMemoryListView(View):
    """The requesting user's AI memory notes, newest first.
    URL: GET /api/financial-advisor/ai/memory/            all notes
         GET /api/financial-advisor/ai/memory/?since=ISO  only notes saved or changed after that moment (the "Saved memory" chip)"""

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        notes = AIMemoryNote.objects.filter(user=request.user)
        since = parse_datetime(request.GET.get("since") or "")
        if since is not None:
            notes = notes.filter(updated_at__gt=since)
        return JsonResponse({"items": [n.to_dict() for n in notes[:200]]})


class AIMemoryDetailView(View):
    """Edit or delete one note of the requesting user.
    URL: PATCH /api/financial-advisor/ai/memory/<id>/   body {"title"?, "body"?}      DELETE the same URL"""

    def _note(self, request, pk):
        return AIMemoryNote.objects.filter(user=request.user, pk=pk).first()

    def patch(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        note = self._note(request, pk)
        if note is None:
            return JsonResponse({"error": "not_found"}, status=404)
        try:
            body = parse_json_body(request)
        except ValueError:
            return JsonResponse({"error": "invalid_body"}, status=400)
        title = " ".join(str(body.get("title", note.title)).split())[:TITLE_MAX]
        text = " ".join(str(body.get("body", note.body)).split())[:BODY_MAX]
        if not title or not text:
            return JsonResponse({"error": "empty_note"}, status=400)
        note.title, note.body = title, text
        note.save()
        return JsonResponse({"item": note.to_dict()})

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        note = self._note(request, pk)
        if note is None:
            return JsonResponse({"error": "not_found"}, status=404)
        note.delete()
        return JsonResponse({"ok": True})
