"""Optional voice sentence-stream safety and Ollama transport tests."""

import io
import json
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase, override_settings
from core.authentication.services import AuthWorkflowService
from ai.integrations.ai_provider.ollama_stream import generate_stream
from core.models import AppSettings
from ai.services.speech import save_speech_settings
from ai.services.speech.voice_stream import (
    begin_voice_stream,
    finish_voice_stream,
    publish_voice_sentence,
    read_voice_sentences,
    stop_voice_stream,
)
from ai.services.usage.metering import MeteredProvider, TokenMeter
from ai.views.ai_chat.chat_pipeline.reason import _VoiceSentenceEmitter
from core.tests.billing.test_support import grant_ai_workspace_access


class VoiceSentenceQueueTests(TestCase):
    def setUp(self):
        begin_voice_stream(7, "turn")

    def test_sentences_are_paginated_and_scoped_to_the_owner(self):
        for number in range(27):
            self.assertTrue(publish_voice_sentence(7, "turn", f"Sentence {number}."))
        first = read_voice_sentences(7, "turn", 0)
        second = read_voice_sentences(7, "turn", first["next"])
        self.assertEqual(len(first["sentences"]), 25)
        self.assertEqual(second["sentences"], ["Sentence 25.", "Sentence 26."])
        self.assertEqual(read_voice_sentences(8, "turn", 0)["sentences"], [])

    def test_blocked_or_finished_stream_rejects_more_text(self):
        stop_voice_stream(7, "turn")
        self.assertFalse(publish_voice_sentence(7, "turn", "Not spoken."))
        finish_voice_stream(7, "turn", failed=True)
        result = read_voice_sentences(7, "turn", 0)
        self.assertTrue(result["blocked"])
        self.assertTrue(result["failed"])
        self.assertTrue(result["done"])

    def test_sentence_emitter_requires_grounded_numbers(self):
        emitted = []
        blocked = []

        def publish(text):
            emitted.append(text)
            return True

        request = SimpleNamespace(
            _voice_sentence_callback=publish,
            _voice_stream_blocker=lambda: blocked.append(True),
        )
        emitter = _VoiceSentenceEmitter(
            request, "What is my balance?", "business_data_analysis", "Current balance: 100 EGP."
        )
        emitter("Your balance is 100 EGP. ")
        emitter.finish()
        self.assertEqual(emitted, ["Your balance is 100 EGP."])
        self.assertEqual(blocked, [])

        unsafe = _VoiceSentenceEmitter(
            request, "What is my balance?", "business_data_analysis", "Current balance: 100 EGP."
        )
        unsafe("Your balance is 999 EGP. ")
        self.assertEqual(blocked, [True])


class OllamaStreamingTests(TestCase):
    def test_existing_providers_keep_their_normal_generate_path(self):
        class LegacyProvider:
            def generate(self, messages, tools=None):
                return {"content": "Complete answer.", "completion_tokens": 2}

        seen = []
        meter = TokenMeter()
        result = MeteredProvider(LegacyProvider(), meter).generate_stream(
            [{"role": "user", "content": "hello"}], on_text=seen.append
        )
        self.assertEqual(result["content"], "Complete answer.")
        self.assertEqual(seen, [])
        self.assertEqual(meter.completion, 2)

    def test_ndjson_content_is_returned_and_forwarded_incrementally(self):
        chunks = [
            {"message": {"content": "Your balance is "}, "done": False},
            {"message": {"content": "100 EGP."}, "done": True, "eval_count": 8},
        ]
        response = io.BytesIO(b"".join((json.dumps(item) + "\n").encode() for item in chunks))
        provider = SimpleNamespace(
            base_url="http://127.0.0.1:11434",
            model="local-model",
            timeout=10,
            user_agent="WealthFlow/test",
            user_options={},
        )
        seen = []
        with patch("ai.integrations.ai_provider.ollama_stream.urllib.request.urlopen", return_value=response) as opened, \
             patch("core.models.AppSettings.get", return_value="auto"):
            result = generate_stream(provider, [{"role": "user", "content": "balance"}], on_text=seen.append)
        self.assertEqual(result["content"], "Your balance is 100 EGP.")
        self.assertEqual(result["completion_tokens"], 8)
        self.assertEqual(seen, ["Your balance is ", "100 EGP."])
        sent = json.loads(opened.call_args.args[0].data.decode())
        self.assertTrue(sent["stream"])
        self.assertNotIn("tools", sent)


@override_settings(DEBUG=True)
class VoiceStreamViewTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="voice-stream-user", password="test-pass")
        profile = AuthWorkflowService.get_profile(user)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        grant_ai_workspace_access(user)
        self.client.force_login(user)

    def tearDown(self):
        AppSettings.objects.filter(owner=None, key__startswith="speech_").delete()

    @override_settings(DEBUG=False)
    def test_sentence_polling_is_disabled_outside_local_development(self):
        response = self.client.get(
            "/api/financial-advisor/ai/speech/voice-chunks/00000000-0000-0000-0000-000000000001/"
        )
        self.assertEqual(response.status_code, 404)

    def test_voice_chat_queues_sentences_for_the_authenticated_turn(self):
        save_speech_settings({
            "speech_tts_enabled": True,
            "speech_tts_endpoint": "http://speech.test/tts",
            "speech_tts_model": "voice",
        })
        turn_id = str(uuid.uuid4())

        def finish_chat(_view, request):
            self.assertTrue(request._voice_sentence_callback("Hello from voice."))
            return HttpResponse("ok")

        with patch(
            "ai.views.ai_chat.ai_chat_core_views.AIChatView.post",
            autospec=True,
            side_effect=finish_chat,
        ):
            response = self.client.post(
                "/api/financial-advisor/ai/chat/voice/",
                json.dumps({"message": "Read this", "voice_stream_id": turn_id}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        polled = self.client.get(f"/api/financial-advisor/ai/speech/voice-chunks/{turn_id}/")
        self.assertEqual(polled.json()["sentences"], ["Hello from voice."])
        self.assertTrue(polled.json()["done"])
