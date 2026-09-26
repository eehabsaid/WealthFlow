"""Tests for the runtime-capability inspection service (item 8/9 of the AI
agent architecture backlog): hardware detection, Ollama /api/show + /api/ps
+ live-benchmark introspection, and the resulting config recommendation.
No live Ollama/hardware dependency — everything below the network boundary
is mocked, same convention as test_semantic_retrieval.py /
test_ai_provider_buy_rate.py.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.authentication.services import AuthWorkflowService
from core.models import AppSettings
from core.services.ai.runtime_capabilities.presets import recommend_config
from core.services.ai.runtime_capabilities.service import inspect_and_recommend

User = get_user_model()


class RecommendConfigTest(TestCase):
    """presets.recommend_config — pure function, no I/O."""

    def setUp(self):
        self.current = {
            "ai_context_size": 4096, "ai_max_tokens": 1024,
            "ai_timeout": 60, "ai_keep_alive": "5m",
        }

    def test_uses_models_own_max_context_capped_by_ram(self):
        result = recommend_config(
            current=self.current,
            model_info={"max_context_length": 32768},
            hardware={"total_ram_gb": 16.0, "gpu_vram_gb": None},
            benchmark=None,
        )
        # 16GB tier caps at 4096 even though the model itself supports 32768.
        self.assertEqual(result["recommended"]["ai_context_size"], 4096)

    def test_unknown_model_context_falls_back_to_ram_tier(self):
        result = recommend_config(
            current=self.current,
            model_info=None,
            hardware={"total_ram_gb": 8.0, "gpu_vram_gb": None},
            benchmark=None,
        )
        self.assertEqual(result["recommended"]["ai_context_size"], 2048)

    def test_max_tokens_derived_from_measured_decode_rate(self):
        result = recommend_config(
            current=self.current,
            model_info=None,
            hardware={"total_ram_gb": 16.0, "gpu_vram_gb": None},
            benchmark={"decode_tok_per_sec": 1.8, "prompt_tok_per_sec": 45.5},
        )
        # 1.8 tok/s * 90s target ~= 162, floored to the 128 minimum? No: 162 > 128.
        self.assertEqual(result["recommended"]["ai_max_tokens"], 162)

    def test_max_tokens_falls_back_when_benchmark_unavailable(self):
        result = recommend_config(
            current=self.current, model_info=None,
            hardware={"total_ram_gb": 16.0, "gpu_vram_gb": None}, benchmark=None,
        )
        self.assertEqual(result["recommended"]["ai_max_tokens"], self.current["ai_max_tokens"])

    def test_timeout_derived_from_measured_rates_not_guessed(self):
        result = recommend_config(
            current=self.current,
            model_info={"max_context_length": 4096},
            hardware={"total_ram_gb": 16.0, "gpu_vram_gb": None},
            benchmark={"decode_tok_per_sec": 1.8, "prompt_tok_per_sec": 45.5},
        )
        # context=4096 @ 45.5 tok/s prompt-eval ~= 90s; max_tokens(162) @ 1.8 tok/s ~= 90s;
        # (90+90)*1.5 = 270s.
        self.assertEqual(result["recommended"]["ai_timeout"], 270)

    def test_keep_alive_shortened_on_limited_hardware(self):
        result = recommend_config(
            current=self.current, model_info=None,
            hardware={"total_ram_gb": 16.0, "gpu_vram_gb": None}, benchmark=None,
        )
        self.assertEqual(result["recommended"]["ai_keep_alive"], "5m")

    def test_keep_alive_extended_with_headroom(self):
        result = recommend_config(
            current=self.current, model_info=None,
            hardware={"total_ram_gb": 64.0, "gpu_vram_gb": None}, benchmark=None,
        )
        self.assertEqual(result["recommended"]["ai_keep_alive"], "30m")

    def test_every_recommendation_has_an_explanatory_note(self):
        result = recommend_config(
            current=self.current, model_info=None,
            hardware={"total_ram_gb": None, "gpu_vram_gb": None}, benchmark=None,
        )
        self.assertEqual(len(result["notes"]), 4)
        self.assertTrue(all(isinstance(n, str) and n for n in result["notes"]))


class InspectAndRecommendTest(TestCase):
    """service.inspect_and_recommend — orchestration, with hardware/Ollama
    calls mocked at their own module boundary."""

    def test_combines_all_sources_and_never_raises_on_full_failure(self):
        with patch("core.services.ai.runtime_capabilities.service.detect_hardware", return_value={"total_ram_gb": None, "gpu_vram_gb": None, "cpu_count": None, "platform": None}), \
             patch("core.services.ai.runtime_capabilities.service.get_model_info", return_value=None), \
             patch("core.services.ai.runtime_capabilities.service.list_running_models", return_value=None), \
             patch("core.services.ai.runtime_capabilities.service.benchmark_generate", return_value=None):
            report = inspect_and_recommend(
                base_url="http://localhost:11434", model="llama3.1:8b",
                current={"ai_context_size": 4096, "ai_max_tokens": 1024, "ai_timeout": 60, "ai_keep_alive": "5m"},
            )
        self.assertIn("recommended", report)
        self.assertIn("notes", report)
        self.assertEqual(report["model"], "llama3.1:8b")

    def test_combines_all_sources_when_everything_succeeds(self):
        with patch("core.services.ai.runtime_capabilities.service.detect_hardware",
                   return_value={"total_ram_gb": 16.0, "gpu_vram_gb": None, "cpu_count": 8, "platform": "Windows"}), \
             patch("core.services.ai.runtime_capabilities.service.get_model_info",
                   return_value={"family": "llama", "parameter_size": "8.0B", "quantization_level": "Q4_K_M", "max_context_length": 131072}), \
             patch("core.services.ai.runtime_capabilities.service.list_running_models",
                   return_value=[{"name": "llama3.1:8b", "size_bytes": 1, "size_vram_bytes": 0, "expires_at": "x"}]), \
             patch("core.services.ai.runtime_capabilities.service.benchmark_generate",
                   return_value={"prompt_tokens": 20, "prompt_eval_seconds": 0.5, "prompt_tok_per_sec": 40.0,
                                 "gen_tokens": 8, "gen_seconds": 4.0, "decode_tok_per_sec": 2.0}):
            report = inspect_and_recommend(
                base_url="http://localhost:11434", model="llama3.1:8b",
                current={"ai_context_size": 4096, "ai_max_tokens": 1024, "ai_timeout": 60, "ai_keep_alive": "5m"},
            )
        self.assertEqual(report["recommended"]["ai_context_size"], 4096)  # capped by RAM tier
        self.assertEqual(report["running_models"][0]["name"], "llama3.1:8b")


class AIRuntimeCapabilitiesViewTest(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username="member_rc", password="pw12345")
        self.admin = User.objects.create_user(username="admin_rc", password="pw12345")
        profile = AuthWorkflowService.get_profile(self.admin)
        profile.is_sysadmin = True
        profile.save()
        AppSettings.set("ai_ollama_url", "http://localhost:11434")
        AppSettings.set("ai_model", "llama3.1:8b")

    def test_requires_admin(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get("/api/settings/ai/runtime-capabilities/").status_code, 403)

    def test_admin_gets_a_full_report(self):
        self.client.force_login(self.admin)
        with patch("core.services.ai.runtime_capabilities.service.detect_hardware",
                   return_value={"total_ram_gb": 16.0, "gpu_vram_gb": None, "cpu_count": 8, "platform": "Windows"}), \
             patch("core.services.ai.runtime_capabilities.service.get_model_info", return_value=None), \
             patch("core.services.ai.runtime_capabilities.service.list_running_models", return_value=[]), \
             patch("core.services.ai.runtime_capabilities.service.benchmark_generate", return_value=None):
            res = self.client.get("/api/settings/ai/runtime-capabilities/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("recommended", body)
        self.assertIn("hardware", body)
        self.assertEqual(body["model"], "llama3.1:8b")
