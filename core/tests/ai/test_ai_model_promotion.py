"""
Model promotion/rollback -> live-chat-model sync tests
(AIModelPromotionSyncTestCase group).

Split out of the former monolithic test_ai_platform.py (200-line rule).
"""

from unittest.mock import patch

from django.test import TestCase
from core.models import AIModelVersion, AppSettings
from core.services.ai.model_manager import AIModelManager


class AIModelPromotionSyncTestCase(TestCase):
    """Covers the fix: promoting/rolling back a model version must actually
    update the 'ai_model' setting that live chat (ollama_provider) reads,
    and base_model defaults must follow whatever model is actually
    configured rather than a hardcoded tag that may not be pulled."""

    def setUp(self):
        AppSettings.set("ai_model", "qwen2.5:3b")

    def test_promote_model_version_syncs_live_chat_model(self):
        AIModelVersion.objects.create(
            version_name="wealthflow-v1", base_model="qwen2.5:3b",
            training_backend="ollama", dataset_version="v1.0",
            benchmark_score=90.0, is_active=True,
        )
        candidate = AIModelVersion.objects.create(
            version_name="wealthflow-v2", base_model="qwen2.5:3b",
            training_backend="ollama", dataset_version="v2.0",
            benchmark_score=95.0, is_active=False,
        )

        self.assertEqual(AppSettings.get("ai_model"), "qwen2.5:3b")
        promoted = AIModelManager.promote_model_version("wealthflow-v2")

        self.assertEqual(promoted.version_name, candidate.version_name)
        self.assertEqual(
            AppSettings.get("ai_model"), "wealthflow-v2",
            "Promoting a version must switch the live chat model, not just a DB flag.",
        )

    def test_rollback_also_syncs_live_chat_model(self):
        AIModelVersion.objects.create(
            version_name="wealthflow-v1", base_model="qwen2.5:3b",
            training_backend="ollama", dataset_version="v1.0",
            benchmark_score=90.0, is_active=False,
        )
        AIModelVersion.objects.create(
            version_name="wealthflow-v2", base_model="qwen2.5:3b",
            training_backend="ollama", dataset_version="v2.0",
            benchmark_score=95.0, is_active=True,
        )
        AppSettings.set("ai_model", "wealthflow-v2")

        AIModelManager.rollback_model_version("wealthflow-v1")

        self.assertEqual(AppSettings.get("ai_model"), "wealthflow-v1")

    def test_trigger_fine_tuning_defaults_to_configured_model_not_llama3(self):
        """Reproduces the reported bug: the base-model default must never be
        a hardcoded tag like llama3:latest that may not be pulled locally —
        it must fall back to whatever the user has actually confirmed works."""
        AppSettings.set("ai_model", "qwen2.5:3b")

        with patch("core.services.ai.model_manager.get_training_backend") as mock_get_backend:
            mock_backend = mock_get_backend.return_value
            mock_backend.train_model.return_value = {"ok": True, "model_version_name": "wealthflow-v2"}

            AIModelManager.trigger_fine_tuning(base_model=None)

            _, kwargs = mock_backend.train_model.call_args
            self.assertEqual(kwargs["base_model_name"], "qwen2.5:3b")
            self.assertNotEqual(kwargs["base_model_name"], "llama3:latest")

    def test_trigger_fine_tuning_respects_explicit_base_model_override(self):
        with patch("core.services.ai.model_manager.get_training_backend") as mock_get_backend:
            mock_backend = mock_get_backend.return_value
            mock_backend.train_model.return_value = {"ok": True, "model_version_name": "wealthflow-v2"}

            AIModelManager.trigger_fine_tuning(base_model="llama3.1:8b")

            _, kwargs = mock_backend.train_model.call_args
            self.assertEqual(kwargs["base_model_name"], "llama3.1:8b")
