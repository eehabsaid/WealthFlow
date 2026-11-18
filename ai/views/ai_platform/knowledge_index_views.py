"""Code knowledge index status (system administrator only): GET = health, POST = refresh now (optionally full rebuild)."""

import json

from django.http import JsonResponse
from django.views import View

from ai.host import user_is_sysadmin
from ai.services.knowledge_index import indexer
from ai.views.ai_platform.auth import _api_auth_required


class AIKnowledgeIndexView(View):
    def _denied(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        if not user_is_sysadmin(request.user):
            return JsonResponse({"error": "Only a system administrator can use the code index"}, status=403)
        return None

    def get(self, request):
        return self._denied(request) or JsonResponse(indexer.status())

    def post(self, request):
        denied = self._denied(request)
        if denied:
            return denied
        try:
            body = json.loads(request.body or b"{}")
        except ValueError:
            body = {}
        result = indexer.refresh(full=bool(body.get("rebuild")))
        return JsonResponse({"result": result, "status": indexer.status()})
