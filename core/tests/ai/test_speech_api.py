"""Speech configuration and OpenAI-compatible STT/TTS client regression tests."""

import json
from unittest.mock import patch
import io
import wave
from django.test import TestCase
from django.contrib.auth import get_user_model
from core.models import AppSettings
from core.services.ai.speech import get_speech_config, save_speech_settings
from core.services.ai.speech.client import transcribe_audio
from core.services.ai.speech.tts import (
    _combine_wav_chunks, build_tts_payload, is_arabic_text, select_tts_profile, synthesize_speech, tts_available,
)


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

    def test_arabic_text_is_detected_by_script_not_by_word_lists(self):
        self.assertTrue(is_arabic_text("أهلاً، عامل إيه؟"))
        self.assertTrue(is_arabic_text("رصيدك 5000 EGP في البنك"))
        self.assertFalse(is_arabic_text("Your balance is 5000 EGP"))
        self.assertFalse(is_arabic_text("Bonjour, ça va ? Guten Tag"))
        self.assertFalse(is_arabic_text("1234 ..."))

    def test_arabic_profile_is_used_only_for_arabic_text(self):
        save_speech_settings({"speech_tts_enabled": True, "speech_tts_endpoint": "http://general.test/speech", "speech_tts_model": "general"})
        save_speech_settings({"speech_tts_ar_enabled": True, "speech_tts_ar_endpoint": "http://arabic.test/v1/audio/speech",
                              "speech_tts_ar_model": "arabic", "speech_tts_ar_voice": r"D:\voices\egyptian_arabic_reference.wav"})
        arabic = select_tts_profile("أهلاً إيهاب، رصيدك كذا")
        self.assertEqual(arabic["endpoint"], "http://arabic.test/v1/audio/speech")
        self.assertEqual(arabic["voice"], r"D:\voices\egyptian_arabic_reference.wav")
        for text in ("Hello there", "Bonjour tout le monde", "Guten Tag"):
            self.assertEqual(select_tts_profile(text)["endpoint"], "http://general.test/speech")

    def test_arabic_text_falls_back_to_general_voice_when_arabic_profile_is_off(self):
        save_speech_settings({"speech_tts_enabled": True, "speech_tts_endpoint": "http://general.test/speech", "speech_tts_model": "general"})
        self.assertEqual(select_tts_profile("مرحبا")["endpoint"], "http://general.test/speech")

    def test_only_arabic_profile_enabled_speaks_arabic_but_not_other_text(self):
        save_speech_settings({"speech_tts_ar_enabled": True, "speech_tts_ar_endpoint": "http://arabic.test/speech", "speech_tts_ar_model": "arabic"})
        self.assertTrue(tts_available())
        self.assertEqual(select_tts_profile("مرحبا")["model"], "arabic")
        with self.assertRaises(RuntimeError):
            select_tts_profile("Hello")

    def test_tts_unavailable_when_nothing_is_enabled(self):
        self.assertFalse(tts_available())
        with self.assertRaises(RuntimeError):
            select_tts_profile("مرحبا")

    def test_payload_matches_the_server_contract_and_has_no_hardcoded_values(self):
        cfg = {"model": "m", "voice": r"D:\ref.wav", "format": "", "language": "auto"}
        self.assertEqual(build_tts_payload(cfg, "نص"), {"model": "m", "input": "نص", "voice": r"D:\ref.wav"})
        cfg.update(format="wav", language="ar")
        self.assertEqual(build_tts_payload(cfg, "x"), {"model": "m", "input": "x", "voice": r"D:\ref.wav",
                                                       "response_format": "wav", "language": "ar"})
        self.assertNotIn("voice", build_tts_payload({"model": "m", "voice": "", "format": "", "language": "auto"}, "x"))

    @patch("core.services.ai.speech.client._request")
    def test_arabic_synthesis_posts_reference_voice_to_the_arabic_endpoint(self, request_mock):
        save_speech_settings({"speech_tts_enabled": True, "speech_tts_endpoint": "http://general.test/speech", "speech_tts_model": "general"})
        save_speech_settings({"speech_tts_ar_enabled": True, "speech_tts_ar_endpoint": "http://arabic.test/v1/audio/speech",
                              "speech_tts_ar_model": "arabic", "speech_tts_ar_voice": r"D:\voices\egyptian_arabic_reference.wav"})
        request_mock.return_value = (b"RIFF-wav", "audio/wav")
        audio, mime = synthesize_speech("أهلاً بيك")
        self.assertEqual((audio, mime), (b"RIFF-wav", "audio/wav"))
        self.assertEqual(request_mock.call_args.args[0], "http://arabic.test/v1/audio/speech")
        payload = json.loads(request_mock.call_args.args[1].decode())
        self.assertEqual(payload["voice"], r"D:\voices\egyptian_arabic_reference.wav")
        self.assertEqual(payload["input"], "أهلاً بيك")

    def test_arabic_profile_settings_are_saved_validated_and_exposed(self):
        with self.assertRaisesMessage(ValueError, "Configure the TTS_AR endpoint and model"):
            save_speech_settings({"speech_tts_ar_enabled": True})
        save_speech_settings({"speech_tts_ar_voice": "ref.wav", "speech_tts_ar_format": "wav"})
        cfg = get_speech_config("tts_ar")
        self.assertEqual((cfg["voice"], cfg["format"], cfg["enabled"]), ("ref.wav", "wav", False))

    def test_wav_chunks_are_combined_into_one_valid_wav(self):
        def wav_bytes(sample):
            out = io.BytesIO()
            with wave.open(out, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(24000)
                wav.writeframes(sample)
            return out.getvalue()
        combined = _combine_wav_chunks([wav_bytes(b"\x00\x00"), wav_bytes(b"\x01\x00")])
        with wave.open(io.BytesIO(combined), "rb") as wav:
            self.assertEqual(wav.getnframes(), 2)
            self.assertEqual(wav.readframes(2), b"\x00\x00\x01\x00")

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
