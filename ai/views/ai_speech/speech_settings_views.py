"""Sysadmin-only speech endpoint diagnostics."""

import json
import logging
from django.http import JsonResponse
from django.views import View
from core.views.auth_views import SysadminRequiredMixin
from core.validators.json_body import parse_json_body
from ai.services.speech import test_speech_endpoint
from ai.services.speech.settings import KINDS, speech_runtime_enabled
from ai.services.speech.voice_sample import VoiceSampleError, delete_voice_sample, save_voice_sample, voice_sample_info

logger = logging.getLogger(__name__)


class SpeechSettingsTestView(SysadminRequiredMixin, View):
    def post(self, request):
        if not speech_runtime_enabled():
            return JsonResponse({"ok": False, "error": "Local speech endpoint tests are disabled outside local development."}, status=404)
        try:
            data = parse_json_body(request)
            kind = str(data.get("kind") or "").strip().lower()
            if kind not in KINDS:
                return JsonResponse({"error": f"kind must be one of {', '.join(KINDS)}"}, status=400)
            result = test_speech_endpoint(kind, data)
            return JsonResponse(result, status=200 if result.get("ok") else 502)
        except (json.JSONDecodeError, ValueError) as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        except Exception:
            logger.exception("Speech endpoint test failed")
            return JsonResponse({"ok": False, "error": "Endpoint test failed; check server logs and endpoint compatibility."}, status=502)


VOICE_REASONS = {"unsupported_type": "Use a .wav, .flac, .mp3 or .ogg recording.", "too_large": "The recording is larger than 20 MB.",
                 "too_small": "The recording is too short to be a voice sample; use 10 to 30 seconds of clear speech."}


class SpeechVoiceSampleView(SysadminRequiredMixin, View):
    """GET -> {has_sample}; POST (multipart `file`) saves the reference voice; DELETE removes it. Sysadmin only."""

    def get(self, request):
        return JsonResponse(voice_sample_info())

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return JsonResponse({"error": "file_required"}, status=400)
        try:
            save_voice_sample(upload.name, upload.read())
        except VoiceSampleError as exc:
            return JsonResponse({"error": str(exc), "message": VOICE_REASONS.get(str(exc), "Upload failed.")}, status=400)
        return JsonResponse(voice_sample_info(), status=201)

    def delete(self, request):
        delete_voice_sample()
        return JsonResponse(voice_sample_info())
