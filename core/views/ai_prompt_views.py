import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.services.ai import AIPromptService


def _api_auth_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None


@method_decorator(csrf_exempt, name="dispatch")
class AIPromptListView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        category_id = request.GET.get("category_id")
        category_code = request.GET.get("category") or request.GET.get("category_code")
        search_query = request.GET.get("search") or request.GET.get("q")
        favorites_only = str(request.GET.get("favorites_only", "")).lower() in ("true", "1")
        sort_by = request.GET.get("sort_by", "favorites")
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 20)

        result = AIPromptService.get_prompts(
            user=request.user,
            category_id=category_id,
            category_code=category_code,
            search_query=search_query,
            favorites_only=favorites_only,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )
        return JsonResponse(result)

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload"}, status=400)

        ok, errors, prompt = AIPromptService.create_prompt(body, user=request.user)
        if not ok:
            return JsonResponse({"error": "Validation failed", "details": errors}, status=400)

        return JsonResponse({"prompt": prompt}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class AIPromptDetailView(View):
    def get(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        prompt = AIPromptService.get_prompt_by_id(pk)
        if not prompt:
            return JsonResponse({"error": "Prompt not found"}, status=404)

        return JsonResponse({"prompt": prompt})

    def put(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload"}, status=400)

        ok, errors, prompt = AIPromptService.update_prompt(pk, body)
        if not ok:
            status_code = 404 if errors.get("error") == "Prompt not found." else 400
            return JsonResponse({"error": "Update failed", "details": errors}, status=status_code)

        return JsonResponse({"prompt": prompt})

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        ok, error = AIPromptService.delete_prompt(pk)
        if not ok:
            return JsonResponse({"error": error}, status=404)

        return JsonResponse({"ok": True, "id": pk})


@method_decorator(csrf_exempt, name="dispatch")
class AIPromptFavoriteView(View):
    def post(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        ok, error, prompt = AIPromptService.toggle_favorite(pk)
        if not ok:
            return JsonResponse({"error": error}, status=404)

        return JsonResponse({"ok": True, "prompt": prompt})


@method_decorator(csrf_exempt, name="dispatch")
class AIPromptUseView(View):
    def post(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        ok, error, prompt = AIPromptService.record_usage(pk)
        if not ok:
            return JsonResponse({"error": error}, status=404)

        return JsonResponse({"ok": True, "prompt": prompt})


@method_decorator(csrf_exempt, name="dispatch")
class AIPromptDuplicateView(View):
    def post(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        ok, error, prompt = AIPromptService.duplicate_prompt(pk)
        if not ok:
            return JsonResponse({"error": error}, status=404)

        return JsonResponse({"ok": True, "prompt": prompt}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class AIPromptCategoryListView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        categories = AIPromptService.get_categories()
        return JsonResponse({"categories": categories})
