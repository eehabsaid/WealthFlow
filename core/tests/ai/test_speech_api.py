"""Speech configuration and OpenAI-compatible STT/TTS client regression tests."""

import json
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from core.models import AppSettings
from core.services.ai.speech import get_speech_config, save_speech_settings
from core.services.ai.speech.client import transcribe_audio, synthesize_speech


class SpeechSettingsTests(TestCase):
    def tearDown(self):
        AppSettings.objects.filter(owner=None, key__startswith="speech_").delete()

    def test_speech_features_are_disabled_by_default(self):
        self.assertFalse(get_speech_config("stt")["enabled"])
        self.assertFalse(get_speech_config("tts")["enabled"])

    def test_settings_are_global_and_api_keys_are_encrypted_and_masked(self):
        save_speech_settings({
            "speech_stt_enabled": True, "speech_stt_provider": "Self-hosted API",
            "speech_stt_endpoint": "http://127.0.0.1:9000/v1/audio/transcriptions",
            "speech_stt_model": "asr-model", "speech_stt_api_key": "secret-token",
            "speech_stt_timeout": 45,
        })
        stored = AppSettings.get("speech_stt_api_key")
        self.assertTrue(stored.startswith("enc:"))
        self.assertNotIn("secret-token", stored)
        config = get_speech_config("stt")
        self.assertTrue(config["enabled"])
        self.assertTrue(config["is_configured"])
        self.assertIn("••••", config["api_key"])

    def test_enabling_requires_endpoint_and_model(self):
        with self.assertRaisesMessage(ValueError, "Configure the STT endpoint and model"):
            save_speech_settings({"speech_stt_enabled": True})
        self.assertFalse(AppSettings.objects.filter(key="speech_stt_enabled", owner=None).exists())


    def test_endpoint_diagnostics_are_sysadmin_only(self):
        payload = json.dumps({"kind": "stt"})
        response = self.client.post("/api/settings/ai/speech/test/", data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 401)
        user = get_user_model().objects.create_user(username="speech-regular-user", password="test-password")
        self.client.force_login(user)
        response = self.client.post("/api/settings/ai/speech/test/", data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    @patch("core.services.ai.speech.client._request")
    def test_transcription_posts_audio_and_reads_text(self, request_mock):
        save_speech_settings({"speech_stt_enabled": True, "speech_stt_endpoint": "http://speech.test/transcribe",
                              "speech_stt_model": "asr", "speech_stt_timeout": 10, "speech_stt_language": "ar"})
        request_mock.return_value = (b'{"text":"hello from audio"}', "application/json")
        self.assertEqual(transcribe_audio(b"audio", "sample.webm", "audio/webm"), "hello from audio")
        args = request_mock.call_args.args
        self.assertEqual(args[0], "http://speech.test/transcribe")
        self.assertIn(b"name=\"file\"", args[1])
        self.assertIn(b"asr", args[1])
        self.assertIn(b'name="language"\r\n\r\nar', args[1])

    @patch("core.services.ai.speech.client._request")
    def test_synthesis_returns_audio_bytes_and_mime_type(self, request_mock):
        save_speech_settings({"speech_tts_enabled": True, "speech_tts_endpoint": "http://speech.test/speech",
                              "speech_tts_model": "voice-model", "speech_tts_voice": "neutral"})
        request_mock.return_value = (b"fake-audio", "audio/mpeg")
        audio, mime = synthesize_speech("Hello")
        self.assertEqual((audio, mime), (b"fake-audio", "audio/mpeg"))
        payload = json.loads(request_mock.call_args.args[1].decode())
        self.assertEqual(payload["model"], "voice-model")
        self.assertEqual(payload["input"], "Hello")
        self.assertEqual(payload["voice"], "neutral")
