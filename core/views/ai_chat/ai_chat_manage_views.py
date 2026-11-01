"""Chat management beyond the basics: search across the user's chats, and edit-and-resend.
Every query is scoped to the requesting user; deleted chats and messages never appear."""

from django.db.models import Q
from django.http import JsonResponse
from django.views import View

from core.models import AIConversation, AIMessage
from core.views.ai_chat.ai_chat_helpers import _api_auth_required

MIN_QUERY = 2
MAX_RESULTS = 30
SNIPPET = 120


def _snippet(text: str, needle: str) -> str:
    flat = " ".join(str(text or "").split())
    at = flat.lower().find(needle.lower())
    start = max(0, at - SNIPPET // 3) if at >= 0 else 0
    return flat[start:start + SNIPPET]


class AIConversationSearchView(View):
    """GET /api/financial-advisor/ai/conversations/search/?q=text -> chats whose title or messages contain the text."""

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        needle = " ".join(str(request.GET.get("q") or "").split())
        if len(needle) < MIN_QUERY:
            return JsonResponse({"results": []})
        chats = AIConversation.objects.filter(user=request.user, is_deleted=False)
        by_title = chats.filter(title__icontains=needle)
        hits = AIMessage.objects.filter(conversation__in=chats, is_deleted=False, content__icontains=needle).order_by("-id")
        results, seen = [], set()
        for chat in by_title[:MAX_RESULTS]:
            seen.add(chat.id)
            results.append({"id": chat.id, "title": chat.title, "snippet": "", "updated_at": chat.updated_at.isoformat()})
        for msg in hits.select_related("conversation")[:MAX_RESULTS * 3]:
            chat = msg.conversation
            if chat.id in seen or len(results) >= MAX_RESULTS:
                continue
            seen.add(chat.id)
            results.append({"id": chat.id, "title": chat.title, "snippet": _snippet(msg.content, needle), "updated_at": chat.updated_at.isoformat()})
        results.sort(key=lambda r: r["updated_at"], reverse=True)
        return JsonResponse({"results": results})


class AIMessageRewindView(View):
    """POST /api/financial-advisor/ai/messages/<id>/rewind/ -> edit-and-resend: this user message and every later message
    of the same chat are hidden (soft-deleted); the page then sends the edited text as a new message."""

    def post(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        msg = AIMessage.objects.filter(pk=pk, role="user", is_deleted=False, conversation__user=request.user, conversation__is_deleted=False).first()
        if msg is None:
            return JsonResponse({"error": "not_found"}, status=404)
        hidden = AIMessage.objects.filter(conversation_id=msg.conversation_id, is_deleted=False).filter(Q(id__gte=msg.id)).update(is_deleted=True)
        return JsonResponse({"ok": True, "hidden": hidden, "conversation_id": msg.conversation_id})
