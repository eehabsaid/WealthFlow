"""Settings > AI Advisor: the "Record Agent answers for training" switch (ai_trace_recording)."""

from django.test import TestCase

from ai.training.services.recorder import enabled as recording_on
from core.models import AppSettings
from ai.views.settings.ai_pipeline_settings import get_pipeline_settings, persist_pipeline_settings, validate_pipeline_settings


class TraceRecordingSettingTests(TestCase):
    def test_default_is_off_and_recorder_agrees(self):
        self.assertIs(get_pipeline_settings()["ai_trace_recording"], False)
        self.assertFalse(recording_on())

    def test_turning_it_on_and_off_reaches_the_recorder(self):
        validated, err = validate_pipeline_settings({"ai_trace_recording": True})
        self.assertIsNone(err)
        persist_pipeline_settings(validated)
        self.assertEqual(AppSettings.get("ai_trace_recording", "", user=None), "true")
        self.assertTrue(get_pipeline_settings()["ai_trace_recording"])
        self.assertTrue(recording_on())
        validated, _ = validate_pipeline_settings({"ai_trace_recording": False})
        persist_pipeline_settings(validated)
        self.assertFalse(recording_on())

    def test_missing_key_keeps_current_value_and_text_values_parse(self):
        AppSettings.set("ai_trace_recording", "true", user=None)
        validated, _ = validate_pipeline_settings({})
        self.assertTrue(validated["trace_recording"])
        validated, _ = validate_pipeline_settings({"ai_trace_recording": "false"})
        self.assertFalse(validated["trace_recording"])
