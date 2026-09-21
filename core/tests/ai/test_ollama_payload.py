from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from core.integrations.ai_provider.ollama_payload import (
    apply_runtime_flags, is_think_unsupported_error, normalize_keep_alive,
    supports_think_toggle)
from core.integrations.ai_provider.ollama_provider import OllamaProvider

_OK = ({"message": {"content": "hi"}}, 200, None)
_PATCH = "core.integrations.ai_provider.ollama_provider.make_json_http_request"


class OllamaPayloadHelpersTests(SimpleTestCase):
    def test_think_toggle_families(self):
        self.assertTrue(supports_think_toggle("qwen3:8b"))
        self.assertTrue(supports_think_toggle("qwen3:4b-instruct"))
        self.assertFalse(supports_think_toggle("qwen3-coder:30b"))
        self.assertFalse(supports_think_toggle("qwen2.5:7b-instruct"))
        self.assertFalse(supports_think_toggle("llama3.1:8b"))
        self.assertFalse(supports_think_toggle(""))

    def test_keep_alive_normalization(self):
        self.assertEqual(normalize_keep_alive("30m"), "30m")
        self.assertEqual(normalize_keep_alive("1h30m"), "1h30m")
        self.assertEqual(normalize_keep_alive("-1"), -1)
        self.assertEqual(normalize_keep_alive("600"), 600)
        self.assertIsNone(normalize_keep_alive(""))
        self.assertIsNone(normalize_keep_alive(None))
        self.assertIsNone(normalize_keep_alive("soon"))

    def test_apply_runtime_flags(self):
        p = apply_runtime_flags({}, "qwen3:8b", "30m")
        self.assertEqual(p, {"think": False, "keep_alive": "30m"})
        p = apply_runtime_flags({}, "llama3.1:8b", "")
        self.assertEqual(p, {})

    def test_think_error_detection(self):
        self.assertTrue(is_think_unsupported_error('"x" does not support thinking'))
        self.assertFalse(is_think_unsupported_error("connection refused"))


class OllamaProviderPayloadTests(TestCase):
    def _provider(self, model="qwen3:8b", keep_alive="30m"):
        p = OllamaProvider(base_url="http://localhost:11434", model=model)
        p.user_options = {"keep_alive": keep_alive}
        return p

    def test_payload_carries_think_false_and_keep_alive(self):
        with patch(_PATCH, return_value=_OK) as m:
            res = self._provider().generate([{"role": "user", "content": "x"}])
        self.assertIsNone(res["error"])
        payload = m.call_args.kwargs["payload"]
        self.assertIs(payload["think"], False)
        self.assertEqual(payload["keep_alive"], "30m")

    def test_non_thinking_model_has_no_think_flag(self):
        with patch(_PATCH, return_value=_OK) as m:
            self._provider(model="llama3.1:8b").generate([{"role": "user", "content": "x"}])
        self.assertNotIn("think", m.call_args.kwargs["payload"])

    def test_retries_without_think_when_rejected(self):
        bad = (None, 400, "model does not support thinking")
        with patch(_PATCH, side_effect=[bad, _OK]) as m:
            res = self._provider().generate([{"role": "user", "content": "x"}])
        self.assertIsNone(res["error"])
        self.assertEqual(m.call_count, 2)
        self.assertNotIn("think", m.call_args_list[1].kwargs["payload"])
