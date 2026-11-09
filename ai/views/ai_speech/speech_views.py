"""Authenticated speech endpoints; providers and credentials remain server-side."""

import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views import View
from core.views.auth_views import PermissionRequiredMixin
from ai.services.speech import (
    get_speech_config, transcribe_audio, synthesize_speech, has_speakable_text,
    tts_available, speech_runtime_enabled,
)

logger = logging.getLogger(__name__)
MAX_SPEECH_INPUT_CHARS = 100000  # sanity cap on the request body; the service chunks and caps what is spoken


class AIWorkspaceSpeechMixin(PermissionRequiredMixin):
    required_key = "wealthflow_ai"


class SpeechCapabilitiesView(AIWorkspaceSpeechMixin, View):
    def get(self, request):
        stt = get_speech_config("stt")
        return JsonResponse({"stt_enabled": speech_runtime_enabled() and stt["enabled"] and stt["is_configured"],
                             "tts_enabled": tts_available()})


class SpeechTranscribeView(AIWorkspaceSpeechMixin, View):
    def post(self, request):
        if not speech_runtime_enabled():
            return JsonResponse({"error": "Local speech is disabled outside local development."}, status=404)
        audio = request.FILES.get("audio")
        if not audio:
            return JsonResponse({"error": "Audio recording is required"}, status=400)
        if audio.size > 25 * 1024 * 1024:
            return JsonResponse({"error": "Audio recording exceeds the 25 MB limit"}, status=413)
        try:
            text = transcribe_audio(audio.read(), audio.name, audio.content_type or "application/octet-stream")
            return JsonResponse({"text": text})
        except Exception:
            logger.exception("Speech transcription request failed")
            return JsonResponse({"error": "Transcription failed. Check the configured speech endpoint and server logs."}, status=502)


class SpeechSynthesizeView(AIWorkspaceSpeechMixin, View):
    def post(self, request):
        if not speech_runtime_enabled():
            return JsonResponse({"error": "Local speech is disabled outside local development."}, status=404)
        try:
            data = json.loads(request.body or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"error": "Invalid JSON body"}, status=400)
        text = str(data.get("text") or "").strip()
        if not text:
            return JsonResponse({"error": "Text is required"}, status=400)
        if len(text) > MAX_SPEECH_INPUT_CHARS:
            return JsonResponse({"error": "Text is too long to read aloud"}, status=400)
        if not has_speakable_text(text):
            return HttpResponse(status=204)  # nothing to say (e.g. a code block): the client just moves on
        try:
            audio, mime = synthesize_speech(text)
            response = HttpResponse(audio, content_type=mime or "audio/mpeg")
            response["Cache-Control"] = "no-store"
            response["X-Content-Type-Options"] = "nosniff"
            return response
        except Exception:
            logger.exception("Speech synthesis request failed")
            return JsonResponse({"error": "Speech generation failed. Check the configured speech endpoint and server logs."}, status=502)
