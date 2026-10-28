"""Sysadmin-only speech endpoint diagnostics."""

import json
import logging
from django.http import JsonResponse
from django.views import View
from core.views.auth_views import SysadminRequiredMixin
from core.validators.json_body import parse_json_body
from core.services.ai.speech import test_speech_endpoint

logger = logging.getLogger(__name__)


class SpeechSettingsTestView(SysadminRequiredMixin, View):
    def post(self, request):
        try:
            data = parse_json_body(request)
            kind = str(data.get("kind") or "").strip().lower()
            if kind not in {"stt", "tts"}:
                return JsonResponse({"error": "kind must be stt or tts"}, status=400)
            result = test_speech_endpoint(kind, data)
            return JsonResponse(result, status=200 if result.get("ok") else 502)
        except (json.JSONDecodeError, ValueError) as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        except Exception:
            logger.exception("Speech endpoint test failed")
            return JsonResponse({"ok": False, "error": "Endpoint test failed; check server logs and endpoint compatibility."}, status=502)
