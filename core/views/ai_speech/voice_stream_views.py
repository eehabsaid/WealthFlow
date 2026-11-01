"""Opt-in voice chat and authenticated polling for sentence-safe stream results."""

import json
import uuid

from django.http import JsonResponse
from django.views import View

from core.services.ai.speech import speech_runtime_enabled, tts_available
from core.services.ai.speech.voice_stream import (
    begin_voice_stream,
    finish_voice_stream,
    publish_voice_sentence,
    read_voice_sentences,
    stop_voice_stream,
)
from core.views.ai_chat.ai_chat_core_views import AIChatView
from core.views.auth_views import PermissionRequiredMixin


class VoiceChatView(AIChatView):
    """Same validated chat pipeline, with an optional local-only voice sentence channel."""

    def post(self, request):
        turn_id = ""
        if request.user.is_authenticated and speech_runtime_enabled() and tts_available():
            try:
                body = json.loads(request.body or b"{}")
                turn_id = str(uuid.UUID(str(body.get("voice_stream_id") or "")))
            except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError, AttributeError):
                turn_id = ""
        if turn_id:
            user_id = request.user.pk
            begin_voice_stream(user_id, turn_id)
            request._voice_question = str(body.get("message") or "")
            request._voice_sentence_callback = lambda text: publish_voice_sentence(user_id, turn_id, text)
            request._voice_stream_blocker = lambda: stop_voice_stream(user_id, turn_id)
            request._voice_stream_failure = lambda: stop_voice_stream(user_id, turn_id, failed=True)
        try:
            return super().post(request)
        finally:
            if turn_id:
                finish_voice_stream(
                    request.user.pk,
                    turn_id,
                    failed=bool(getattr(request, "_voice_stream_failed", False)),
                )


class VoiceSentencePollView(PermissionRequiredMixin, View):
    required_key = "wealthflow_ai"

    def get(self, request, turn_id):
        if not speech_runtime_enabled() or not tts_available():
            return JsonResponse({"error": "Local speech is disabled."}, status=404)
        try:
            offset = int(request.GET.get("after", "0"))
        except ValueError:
            return JsonResponse({"error": "Invalid sentence offset."}, status=400)
        if offset < 0 or offset > 250:
            return JsonResponse({"error": "Invalid sentence offset."}, status=400)
        return JsonResponse(read_voice_sentences(request.user.pk, str(turn_id), offset))
