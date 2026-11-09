"""Voice cloning: the reference voice is uploaded in Settings and used by Chatterbox voice profiles that have no voice of their own."""

import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from core.authentication.services import AuthWorkflowService
from core.models import AppSettings
from ai.services.speech.tts import _with_uploaded_voice
from ai.services.speech.voice_sample import VoiceSampleError, delete_voice_sample, save_voice_sample, voice_sample_path

URL = "/api/settings/ai/speech/voice-sample/"
WAV = b"RIFF" + b"\x00" * 40000


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class VoiceCloneTests(TestCase):
    def tearDown(self):
        from django.conf import settings
        shutil.rmtree(os.path.join(settings.MEDIA_ROOT, "voice_samples"), ignore_errors=True)
        AppSettings.objects.filter(owner=None, key__startswith="speech_").delete()

    def test_save_replaces_the_old_file_and_delete_removes_it(self):
        first = save_voice_sample("me.wav", WAV)
        second = save_voice_sample("me.flac", WAV)
        self.assertFalse(os.path.exists(first))
        self.assertEqual(voice_sample_path(), second)
        delete_voice_sample()
        self.assertEqual(voice_sample_path(), "")
        self.assertFalse(os.path.exists(second))

    def test_bad_recordings_refused(self):
        for name, raw, why in (("me.exe", WAV, "unsupported_type"), ("me.wav", b"x", "too_small"), ("me.wav", b"x" * (20 * 1024 * 1024 + 1), "too_large")):
            with self.assertRaises(VoiceSampleError) as ctx:
                save_voice_sample(name, raw)
            self.assertEqual(str(ctx.exception), why)

    def test_a_missing_file_counts_as_no_sample(self):
        path = save_voice_sample("me.wav", WAV)
        os.remove(path)
        self.assertEqual(voice_sample_path(), "")

    def test_chatterbox_profile_without_a_voice_uses_the_uploaded_sample(self):
        path = save_voice_sample("me.wav", WAV)
        self.assertEqual(_with_uploaded_voice({"model": "chatterbox-multilingual-v3", "voice": ""})["voice"], path)

    def test_a_voice_set_in_the_profile_is_never_replaced(self):
        save_voice_sample("me.wav", WAV)
        cfg = {"model": "chatterbox-multilingual-v3", "voice": "/srv/egyptian.wav"}
        self.assertEqual(_with_uploaded_voice(cfg)["voice"], "/srv/egyptian.wav")

    def test_other_models_and_no_sample_are_left_alone(self):
        cfg = {"model": "piper", "voice": ""}
        save_voice_sample("me.wav", WAV)
        self.assertEqual(_with_uploaded_voice(cfg), cfg)
        delete_voice_sample()
        cfg = {"model": "chatterbox-multilingual-v3", "voice": ""}
        self.assertEqual(_with_uploaded_voice(cfg), cfg)

    def test_upload_view_is_sysadmin_only_and_works_for_sysadmin(self):
        User = get_user_model()
        member = User.objects.create_user(username="member", password="pw12345!")
        self.client.force_login(member)
        self.assertEqual(self.client.post(URL, {"file": SimpleUploadedFile("me.wav", WAV)}).status_code, 403)
        self.assertEqual(self.client.delete(URL).status_code, 403)
        admin = User.objects.create_user(username="admin", password="pw12345!")
        profile = AuthWorkflowService.get_profile(admin)
        profile.is_sysadmin = True
        profile.save()
        self.client.force_login(admin)
        self.assertEqual(self.client.post(URL, {"file": SimpleUploadedFile("me.wav", WAV)}).status_code, 201)
        self.assertTrue(self.client.get(URL).json()["has_sample"])
        self.assertEqual(self.client.post(URL, {"file": SimpleUploadedFile("me.mp4", WAV)}).status_code, 400)
        self.assertFalse(self.client.delete(URL).json()["has_sample"])
