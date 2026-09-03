import json
import time

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.models import AIConversation
from core.services.ai.cache_manager import AICacheManager
from core.views.ai_chat.ai_chat_helpers import _api_auth_required


@method_decorator(csrf_exempt, name="dispatch")
class AIProgressView(View):
    """
    Lightweight progress polling endpoint for the multi-step investigation loop.
    URL: GET /api/financial-advisor/ai/progress/?conversation_id=<id>

    Returns the current loop step, tool name, and elapsed time for the requesting
    user's active investigation. The frontend polls this every 2 seconds while
    loading to update the typing bubble with live step information.

    Auth: session-authenticated (same pattern as all other AI endpoints).
    Ownership: progress key is scoped to user.id × conversation.id — a different
    user cannot see another user's progress even if they guess the conversation ID.
    Additionally, the conversation ownership is explicitly verified below.
    """

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        conversation_id = request.GET.get("conversation_id", "")
        try:
            conv_id = int(conversation_id)
        except (ValueError, TypeError):
            return JsonResponse({"status": "idle"})

        # Explicit ownership check: the conversation must belong to this user
        try:
            AIConversation.objects.get(id=conv_id, user=request.user, is_deleted=False)
        except AIConversation.DoesNotExist:
            # Return idle rather than 403 to avoid leaking conversation existence
            return JsonResponse({"status": "idle"})

        cache_mgr = AICacheManager()
        progress_key = f"ai_loop_progress:{request.user.id}:{conv_id}"
        state = cache_mgr.get(progress_key)

        if state and isinstance(state, dict):
            res_state = dict(state)
            if res_state.get("status") == "running" and "started_at" in res_state:
                res_state["elapsed_s"] = round(time.time() - float(res_state["started_at"]), 1)
            return JsonResponse(res_state)

        return JsonResponse({"status": "idle"})

@method_decorator(csrf_exempt, name="dispatch")
class AIConversationListView(View):
    """
    View for listing and creating conversations.
    URL: GET/POST /api/financial-advisor/ai/conversations/
    """

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        qs = AIConversation.objects.filter(user=request.user, is_deleted=False)
        if request.GET.get("pinned") == "true":
            qs = qs.filter(is_pinned=True)

        cache_mgr = AICacheManager()
        data = []
        for c in qs:
            c_dict = c.to_dict()
            prog_key = f"ai_loop_progress:{request.user.id}:{c.id}"
            st = cache_mgr.get(prog_key)
            is_running = bool(st and isinstance(st, dict) and st.get("status") == "running")
            c_dict["is_running"] = is_running
            data.append(c_dict)

        return JsonResponse({"conversations": data})

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            body = {}

        title = str(body.get("title", "New Conversation")).strip() or "New Conversation"
        conversation = AIConversation.objects.create(user=request.user, title=title)
        return JsonResponse({"conversation": conversation.to_dict()}, status=201)

@method_decorator(csrf_exempt, name="dispatch")
class AIConversationDetailView(View):
    """
    View for viewing or soft-deleting a conversation.
    URL: GET/DELETE /api/financial-advisor/ai/conversations/<int:pk>/
    """

    def get(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            conversation = AIConversation.objects.get(id=pk, user=request.user, is_deleted=False)
        except AIConversation.DoesNotExist:
            return JsonResponse({"error": "Conversation not found"}, status=404)

        messages = conversation.messages.filter(is_deleted=False)
        msg_list = [m.to_dict() for m in messages]

        conv_dict = conversation.to_dict()
        conv_dict["messages"] = msg_list

        # Check running state — cache key is the only reliable signal
        cache_mgr = AICacheManager()
        prog_key = f"ai_loop_progress:{request.user.id}:{conversation.id}"
        st = cache_mgr.get(prog_key)
        is_running = bool(st and isinstance(st, dict) and st.get("status") == "running")
        conv_dict["is_running"] = is_running

        return JsonResponse({"conversation": conv_dict})

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            conversation = AIConversation.objects.get(id=pk, user=request.user, is_deleted=False)
        except AIConversation.DoesNotExist:
            return JsonResponse({"error": "Conversation not found"}, status=404)

        # Soft delete conversation and its messages
        conversation.is_deleted = True
        conversation.save(update_fields=["is_deleted", "updated_at"])
        conversation.messages.filter(is_deleted=False).update(is_deleted=True)

        return JsonResponse({"ok": True, "id": pk})

    def patch(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            conversation = AIConversation.objects.get(id=pk, user=request.user, is_deleted=False)
        except AIConversation.DoesNotExist:
            return JsonResponse({"error": "Conversation not found"}, status=404)

        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            body = {}

        if "is_pinned" in body:
            conversation.is_pinned = bool(body["is_pinned"])
            conversation.save(update_fields=["is_pinned"])

        return JsonResponse({"conversation": conversation.to_dict()})
