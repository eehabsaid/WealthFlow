"""Reasoning text from thinking models must never reach the answer, the grounding check or the user."""

from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from core.integrations.ai_provider.ollama_provider import OllamaProvider
from core.integrations.ai_provider.ollama_response import parse_message, strip_reasoning

_PATCH = "core.integrations.ai_provider.ollama_provider.make_json_http_request"


class StripReasoningTests(SimpleTestCase):
    def test_plain_answer_unchanged(self):
        self.assertEqual(strip_reasoning("7,176,242.07 EGP"), "7,176,242.07 EGP")
        self.assertEqual(strip_reasoning(""), "")

    def test_think_block_removed(self):
        self.assertEqual(strip_reasoning("<think>work it out\n292,900.00</think>\n\n7,176,242.07 EGP"), "7,176,242.07 EGP")
        self.assertEqual(strip_reasoning("<THINK>a</THINK>x<think>b</think>y"), "xy")

    def test_closing_tag_only_drops_everything_before_it(self):
        raw = "We are given the data.\nThe example is 292,900.00 EGP.\n</think>\n\n7,176,242.07 EGP"
        self.assertEqual(strip_reasoning(raw), "7,176,242.07 EGP")

    def test_unclosed_block_is_all_reasoning(self):
        self.assertEqual(strip_reasoning("Answer start <think>still thinking, cut off"), "Answer start")
        self.assertEqual(strip_reasoning("<think>only reasoning"), "")

    def test_only_tags_are_touched(self):
        text = "I think the total is 5 and thinking about it again, still 5."
        self.assertEqual(strip_reasoning(text), text)


class ParseMessageTests(SimpleTestCase):
    def test_tool_call_recovered_after_reasoning(self):
        raw = '<think>need a tool</think>{"name": "query_application_data", "arguments": {"q": "x"}}'
        content, calls = parse_message({"content": raw})
        self.assertEqual(content, "")
        self.assertEqual(calls[0]["function"]["name"], "query_application_data")

    def test_real_tool_calls_field_untouched(self):
        calls = [{"function": {"name": "n", "arguments": {}}}]
        content, got = parse_message({"content": "ok", "tool_calls": calls})
        self.assertEqual((content, got), ("ok", calls))


class ProviderGenerateTests(TestCase):
    def test_generate_returns_clean_content(self):
        data = {"message": {"content": "reasoning 292,900.00\n</think>\n\n7,176,242.07 EGP"}}
        with patch(_PATCH, return_value=(data, 200, None)):
            res = OllamaProvider(model="qwen3:30b-a3b").generate([{"role": "user", "content": "q"}])
        self.assertEqual(res["content"], "7,176,242.07 EGP")
        self.assertNotIn("292,900.00", res["content"])
