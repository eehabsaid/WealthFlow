"""
Knowledge Base management views (AI Platform).

Split out of the former monolithic ai_platform_views.py (200-line rule).
"""

import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.models import AIKnowledgeEntry
from core.services.ai.autonomous_learning_engine import AIAutonomousLearningEngine
from core.services.ai.knowledge_engine import AIKnowledgeEngine
from core.views.ai_platform_views.auth import _api_auth_required


@method_decorator(csrf_exempt, name="dispatch")
class AIPlatformKnowledgeView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        category = request.GET.get("category")
        search = request.GET.get("search", "").strip()
        entries = AIKnowledgeEngine.get_active_knowledge_entries(category=category)
        if search:
            sl = search.lower()
            entries = [
                e
                for e in entries
                if (e.title and sl in e.title.lower())
                or (e.content and sl in e.content.lower())
                or (e.key and sl in e.key.lower())
            ]
        return JsonResponse({"entries": [e.to_dict() for e in entries]})

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            body = {}

        action = str(body.get("action", "scan")).strip().lower()
        if action == "scan":
            res = AIAutonomousLearningEngine.scan_and_learn_application_evolution()
            return JsonResponse(res)

        key = str(body.get("key", "")).strip()
        title = str(body.get("title", "")).strip()
        content = str(body.get("content", "")).strip()
        category = str(body.get("category", "business_rule")).strip()

        if not key or not title or not content:
            return JsonResponse({"error": "Key, title, and content are required"}, status=400)

        entry = AIKnowledgeEngine.record_knowledge_entry(
            key=key,
            title=title,
            content=content,
            category=category,
            source="user_manual",
        )
        return JsonResponse({"entry": entry.to_dict()}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class AIPlatformKnowledgeDetailView(View):
    """
    Per-entry knowledge operations.
    URL: PATCH/DELETE /api/ai-platform/knowledge/<int:pk>/
    """

    def patch(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            entry = AIKnowledgeEntry.objects.get(id=pk)
        except AIKnowledgeEntry.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            body = {}

        if "title" in body:
            entry.title = str(body["title"]).strip()
        if "content" in body:
            entry.content = str(body["content"]).strip()
        if "category" in body:
            entry.category = str(body["category"]).strip()
        entry.save()
        return JsonResponse({"entry": entry.to_dict()})

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            entry = AIKnowledgeEntry.objects.get(id=pk)
        except AIKnowledgeEntry.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        entry.delete()
        return JsonResponse({"ok": True, "id": pk})
