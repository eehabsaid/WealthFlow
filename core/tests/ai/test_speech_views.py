"""Speech API views (capabilities / transcribe / synthesize) and the Markdown -> speakable-text preparation."""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from core.authentication.services import AuthWorkflowService
from core.models import AppSettings
from core.services.ai.speech import save_speech_settings
from core.services.ai.speech.client import synthesize_speech
from core.services.ai.speech.text_prep import speakable_text, speech_chunks
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()
CAPS = "/api/financial-advisor/ai/speech/capabilities/"
STT = "/api/financial-advisor/ai/speech/transcribe/"
TTS = "/api/financial-advisor/ai/speech/synthesize/"
VIEWS = "core.views.ai_speech.speech_views"


def _json(client, url, payload):
    return client.post(url, json.dumps(payload), content_type="application/json")


class SpeechViewsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="speech-admin", password="pw12345!")
        profile = AuthWorkflowService.get_profile(self.admin)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        grant_ai_workspace_access(self.admin)
        self.client.force_login(self.admin)

    def tearDown(self):
        AppSettings.objects.filter(owner=None, key__startswith="speech_").delete()

    def test_capabilities_follow_configuration(self):
        self.assertEqual(self.client.get(CAPS).json(), {"stt_enabled": False, "tts_enabled": False})
        save_speech_settings({"speech_tts_enabled": True, "speech_tts_endpoint": "http://speech.test/tts", "speech_tts_model": "voice"})
        self.assertEqual(self.client.get(CAPS).json(), {"stt_enabled": False, "tts_enabled": True})

    def test_access_is_gated_by_login_plan_and_permission(self):
        self.client.logout()
        self.assertEqual(self.client.get(CAPS).status_code, 401)
        no_plan = User.objects.create_user(username="speech-noplan", password="pw12345!")
        self.client.force_login(no_plan)
        self.assertEqual(self.client.get(CAPS).status_code, 402)
        no_role = User.objects.create_user(username="speech-norole", password="pw12345!")
        grant_ai_workspace_access(no_role)
        self.client.force_login(no_role)
        for url in (CAPS, STT, TTS):
            self.assertEqual(self.client.generic("GET" if url == CAPS else "POST", url).status_code, 403)

    def test_transcribe_validates_the_upload(self):
        self.assertEqual(self.client.post(STT, {}).status_code, 400)
        big = SimpleUploadedFile("big.webm", b"0" * (25 * 1024 * 1024 + 1), content_type="audio/webm")
        self.assertEqual(self.client.post(STT, {"audio": big}).status_code, 413)

    def test_transcribe_returns_text(self):
        audio = SimpleUploadedFile("rec.webm", b"audio", content_type="audio/webm")
        with patch(f"{VIEWS}.transcribe_audio", return_value="hello") as mocked:
            response = self.client.post(STT, {"audio": audio})
        self.assertEqual(response.json(), {"text": "hello"})
        self.assertEqual(mocked.call_args.args[0], b"audio")

    def test_transcribe_failure_hides_provider_details(self):
        audio = SimpleUploadedFile("rec.webm", b"audio", content_type="audio/webm")
        with patch(f"{VIEWS}.transcribe_audio", side_effect=RuntimeError("secret-host:9000 refused")):
            response = self.client.post(STT, {"audio": audio})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("secret-host", response.content.decode())

    def test_synthesize_validates_the_body(self):
        self.assertEqual(self.client.post(TTS, "{bad", content_type="application/json").status_code, 400)
        self.assertEqual(_json(self.client, TTS, {"text": "  "}).status_code, 400)
        self.assertEqual(_json(self.client, TTS, {"text": "a" * 100001}).status_code, 400)

    def test_synthesize_returns_audio_that_is_not_cached(self):
        with patch(f"{VIEWS}.synthesize_speech", return_value=(b"mp3-bytes", "audio/mpeg")) as mocked:
            response = _json(self.client, TTS, {"text": "x" * 20000})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"mp3-bytes")
        self.assertEqual(response["Content-Type"], "audio/mpeg")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(len(mocked.call_args.args[0]), 20000)

    def test_synthesize_failure_hides_provider_details(self):
        with patch(f"{VIEWS}.synthesize_speech", side_effect=RuntimeError("secret-host:9000 refused")):
            response = _json(self.client, TTS, {"text": "hello"})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("secret-host", response.content.decode())


class SpeechTextPrepTests(TestCase):
    SAMPLE = "## Summary\n\nYour **balance** is `5,000` EGP, see [the report](/x/).\n\n| Month | Paid |\n|---|---|\n| Jan | 100 |\n\n- first item\n1. second step"

    def test_markdown_symbols_are_removed(self):
        text = speakable_text(self.SAMPLE)
        for symbol in ("#", "**", "`", "|", "](", "---"):
            self.assertNotIn(symbol, text)
        self.assertIn("Summary.", text)
        self.assertIn("the report", text)
        self.assertIn("Month: Jan, Paid: 100.", text)
        self.assertIn("first item", text)

    def test_chunks_respect_the_limit_and_the_cap(self):
        long_line = "word " * 3000
        chunks = speech_chunks(long_line, limit=500)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= 500 for c in chunks))
        self.assertEqual(len(speech_chunks("para\n" * 400, limit=10, max_chunks=3)), 3)
        self.assertEqual(speech_chunks("  \n\n "), [])

    @patch("core.services.ai.speech.client._request")
    def test_long_answer_is_sent_in_clean_chunks_and_joined(self, request_mock):
        save_speech_settings({"speech_tts_enabled": True, "speech_tts_endpoint": "http://speech.test/tts", "speech_tts_model": "voice"})
        request_mock.side_effect = lambda url, body, headers, timeout: (b"A", "audio/mpeg")
        answer = "\n\n".join(f"**Point {i}** " + "word " * 200 for i in range(12))
        try:
            audio, mime = synthesize_speech(answer)
        finally:
            AppSettings.objects.filter(owner=None, key__startswith="speech_").delete()
        self.assertGreater(request_mock.call_count, 1)
        self.assertEqual((audio, mime), (b"A" * request_mock.call_count, "audio/mpeg"))
        for call in request_mock.call_args_list:
            sent = json.loads(call.args[1].decode())["input"]
            self.assertNotIn("**", sent)
            self.assertLessEqual(len(sent), 3500)
