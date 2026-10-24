"""The REAL OllamaProvider (payload building, think flag, tool-call parsing, timeouts) against tests/support/fake_ollama.py.

Proves routing, payloads and files. It does NOT prove the quality of real qwen3.8 output or real timings."""

from __future__ import annotations

import threading
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from core.integrations.ai_provider.ollama_provider import OllamaProvider
from core.services.ai.investigation.compose import compose_document
from tests.support import fake_ollama as fo

from .support import make_user
from .test_compose_guide import GuideProvider, Result

THINK = "core.integrations.ai_provider.ollama_provider.think_setting"   # the name the provider imported


def provider(server, timeout: int = 20) -> OllamaProvider:
    p = OllamaProvider(base_url=server.url, model=fo.MODEL, timeout=timeout)
    p.user_options.update({"context_size": "98304", "max_tokens": "4096"})
    return p


class ProviderAgainstFakeTest(TestCase):
    def test_the_three_reasoning_modes_are_honoured_in_the_payload(self):
        with fo.FakeOllama(handler=lambda p: fo.reply("ok")) as server:
            prov = provider(server)
            for setting, hint, expected in (("off", "on", False), ("on", "off", True), ("auto", "on", True), ("auto", "off", False), ("auto", None, False)):
                with patch(THINK, return_value=setting):
                    prov.generate([{"role": "user", "content": "hi"}], reasoning=hint)
                self.assertIs(server.think_flags()[-1], expected, (setting, hint))
            self.assertEqual(server.requests[0]["options"].get("num_ctx"), 98304)

    def test_content_thinking_field_inline_think_and_tool_calls_are_parsed(self):
        replies = [fo.with_thinking("YES"), fo.reply("answer", inline_think="hidden"), fo.reply("", tool_calls=[fo.tool_call("app_routes", page="expenses")]),
                   fo.truncated(), fo.empty()]
        with fo.FakeOllama(replies=replies) as server:
            prov = provider(server)
            out = [prov.generate([{"role": "user", "content": "x"}]) for _ in replies]
        self.assertEqual(out[0]["content"], "YES")
        self.assertEqual(out[1]["content"], "answer")
        self.assertEqual(out[2]["tool_calls"][0]["function"]["name"], "app_routes")
        self.assertEqual(out[3]["done_reason"], "length")
        self.assertEqual(out[4]["content"], "")

    def test_a_slow_reply_past_the_timeout_is_an_error_not_a_hang(self):
        with fo.FakeOllama(replies=[fo.slow("late", 3)]) as server:
            res = provider(server).generate([{"role": "user", "content": "x"}], timeout=1)
        self.assertTrue(res["error"])

    def test_requests_queue_one_at_a_time(self):
        with fo.FakeOllama(handler=lambda p: fo.slow("done", 0.4)) as server:
            prov, results = provider(server), []
            threads = [threading.Thread(target=lambda: results.append(prov.generate([{"role": "user", "content": "x"}]))) for _ in range(3)]
            [t.start() for t in threads]
            [t.join() for t in threads]
        self.assertEqual(len(results), 3)
        self.assertFalse(server.overlapping())
        self.assertTrue(any(r["queued"] for r in server.requests))

    def test_connection_and_model_listing_endpoints(self):
        with fo.FakeOllama() as server:
            prov = provider(server)
            self.assertTrue(prov.check_connection().get("success", True))
            self.assertTrue(prov.check_model_available(fo.MODEL))


class ClassifierRepliesTest(TestCase):
    """What the one-word question may come back as, through the real provider."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("fake_ollama_admin", sysadmin=True)

    def classify(self, replies):
        from core.services.ai.investigation.compose import _about_the_app

        out = SimpleNamespace(llm_calls=0, cut_off=False, cancelled=False, cancel_check=None)
        with fo.FakeOllama(replies=list(replies), handler=lambda p: fo.empty()) as server:
            with patch(THINK, return_value="auto"):
                answer = _about_the_app(provider(server), "write the user guide", out, __import__("time").monotonic() + 100)
            return answer, server

    def test_lenient_variants_and_the_retry_with_reasoning(self):
        for reply, expected in ((fo.yes(), True), (fo.reply("**Yes.**"), True), (fo.with_thinking("YES"), True), (fo.no(), False)):
            self.assertIs(self.classify([reply])[0], expected)
        answer, server = self.classify([fo.empty(), fo.yes()])
        self.assertTrue(answer)
        self.assertEqual(server.think_flags(), [False, True])      # empty with reasoning off -> asked once more with reasoning on
        self.assertFalse(self.classify([fo.gibberish(), fo.gibberish()])[0])
        self.assertFalse(self.classify([fo.arabic_yes(), fo.arabic_yes()])[0])   # not the protocol: no usable answer, the structural rule decides


class GuideThroughRealProviderTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("fake_ollama_guide", sysadmin=True)

    def test_guide_is_written_with_reasoning_off_for_every_section_and_a_code_request_stays_code(self):
        script = GuideProvider()
        script.user = self.admin
        from core.services.ai.investigation.compose_sections import units

        plan = units(self.admin)   # read here: the fake server answers from another thread and must not touch the test database
        with fo.FakeOllama(handler=lambda p: fo.reply(script.generate(p["messages"])["content"])) as server, patch(THINK, return_value="auto"), \
                patch("core.tests.ai.investigation.test_compose_guide.units", return_value=plan):
            res = Result()
            text = compose_document(provider(server), "write the user guide as a word document", res, 24000, self.admin, strict=True)
            self.assertTrue(text.startswith("# "))
            self.assertGreater(text.count("\n## "), 5)
            self.assertTrue(server.requests and not any(server.think_flags()))   # classifier, sections and translation never think in auto mode
            page = Result()
            page.content = '<!doctype html><form><input type="password"><button>Log in</button></form>'
            before = len(server.requests)
            self.assertEqual(compose_document(provider(server), "write an html login page", page, 24000, self.admin, strict=True), "")
            self.assertGreater(len(server.requests), before)   # the classifier was asked; the model's own page was kept
