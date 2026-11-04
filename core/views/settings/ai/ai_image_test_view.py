"""Sysadmin-only connection test for the image generation provider, using the values currently typed in the settings form."""

import json
import logging

from django.http import JsonResponse
from django.views import View

from core.services.ai.credential_encryption import is_masked
from core.services.ai.image_generation import test_connection
from core.services.ai.image_generation.providers import ImageProviderError
from core.validators.json_body import parse_json_body
from core.views.auth_views import SysadminRequiredMixin

logger = logging.getLogger(__name__)


class ImageSettingsTestView(SysadminRequiredMixin, View):
    """POST {image_gen_provider, image_gen_model, image_gen_endpoint, image_gen_api_key} -> {ok, detail | error}"""

    def post(self, request):
        try:
            data = parse_json_body(request)
        except json.JSONDecodeError:
            return JsonResponse({"ok": False, "error": "Invalid JSON body"}, status=400)
        overrides = {f: str(data.get(f"image_gen_{f}") or "").strip() for f in ("provider", "model", "endpoint", "api_key")}
        if is_masked(overrides["api_key"]):
            overrides["api_key"] = ""   # an unchanged masked key means "use the saved one"
        endpoint = overrides["endpoint"]
        if endpoint and not endpoint.lower().startswith(("http://", "https://")):
            return JsonResponse({"ok": False, "error": "API URL must start with http:// or https://"}, status=400)
        try:
            return JsonResponse({"ok": True, "detail": test_connection(overrides)})
        except ImageProviderError as exc:
            return JsonResponse({"ok": False, "error": str(exc)}, status=502)
        except Exception:
            logger.exception("Image provider connection test failed")
            return JsonResponse({"ok": False, "error": "Connection test failed; check the server log."}, status=502)
