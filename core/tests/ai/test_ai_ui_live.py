"""Real-browser test of the AI Workspace learning loop (Chromium via Playwright, stub model, real UI and server).

ask -> answer with thumbs bar -> thumbs up -> Learned Answers modal -> similar question gets the approved answer in
its prompt -> model timeout shows the retrieved facts. Skipped when Playwright/Chromium is not installed."""

from __future__ import annotations

import os
from unittest.mock import patch

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.cache import cache

from core.models import AIAnswerFeedback, PagePermission
from core.tests.ai import qe_fixtures as fx
from core.tests.ai.test_ai_workflow_chat import LAPTOP, PROVIDER, stub_provider

SIMILAR = "I just bought a laptop, should I record its price in assets or in expenses?"
ANSWER = "Record it as an asset: the purchase price already deducts your balance."


class AIWorkspaceLiveTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"   # Playwright's sync API runs an event loop in this thread
        super().setUpClass()
        try:
            from playwright.sync_api import sync_playwright

            cls._pw = sync_playwright().start()
            cls._browser = cls._pw.chromium.launch(headless=True, args=["--no-sandbox"])
        except Exception as exc:   # no playwright / no browser: run scripts/run_full_e2e.py instead
            super().tearDownClass()
            from unittest import SkipTest
            raise SkipTest(f"Chromium not available: {str(exc).splitlines()[0]}")

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()
        super().tearDownClass()

    def setUp(self):
        cache.clear()
        fx.build(self)
        PagePermission.objects.create(user=self.user, page="wealthflow_ai", granted=True)
        self.client.force_login(self.user)
        ctx = self._browser.new_context(viewport={"width": 1280, "height": 900})
        ctx.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                          "url": self.live_server_url}])
        self.page = ctx.new_page()
        self.addCleanup(ctx.close)

    def skip_onboarding(self):
        """A brand-new user gets the first-run wizard on top of the page; skip it like a user would."""
        skip = self.page.locator("#globalModal.show button:has-text('Skip for now')")
        try:
            skip.wait_for(state="visible", timeout=6000)
        except Exception:
            return
        skip.click()
        self.page.wait_for_selector("#globalModal.show", state="detached", timeout=8000)

    def open_ai(self):
        self.page.goto(f"{self.live_server_url}/#ai")
        self.skip_onboarding()
        if "#ai" not in self.page.url:
            self.page.goto(f"{self.live_server_url}/#ai")
        self.page.wait_for_selector("#ai-ws-input", timeout=15000)

    def ask(self, text, expect):
        """Send and wait for a NEW assistant bubble containing `expect` (earlier bubbles may contain it too)."""
        before = self.page.locator(f".ai-ws-msg-content:has-text('{expect}')").count()
        bubbles = self.page.locator(".ai-ws-msg-content").count()
        self.page.fill("#ai-ws-input", text)
        self.page.press("#ai-ws-input", "Enter")
        self.page.wait_for_function(
            "([sel, n]) => document.querySelectorAll(sel).length > n",
            arg=[".ai-ws-msg-content", bubbles + 1], timeout=20000)
        self.page.wait_for_selector(f".ai-ws-msg-content:has-text('{expect}') >> nth={before}", timeout=20000)

    def test_full_learning_loop(self):
        prov = stub_provider(reply=ANSWER)
        with patch(PROVIDER, return_value=prov):
            self.open_ai()
            self.ask(LAPTOP, "purchase price already deducts")
            self.page.wait_for_selector(".ai-ws-feedback .ai-ws-fb-up", timeout=5000)
            self.assertEqual(self.page.locator(".ai-ws-feedback").count(), 1)       # assistant only, not the user bubble

            self.page.click(".ai-ws-fb-up")
            self.page.wait_for_selector(".ai-ws-fb-up.active", timeout=5000)
            row = AIAnswerFeedback.objects.get(owner=self.user)
            self.assertEqual((row.rating, row.kind, row.question, row.answer), (1, "workflow", LAPTOP, ANSWER))

            self.page.click("#ai-ws-card-learned-answers")
            self.page.wait_for_selector(".la-row", timeout=5000)
            self.assertIn("laptop", self.page.inner_text(".la-row").lower())
            self.assertIn("Reused", self.page.inner_text(".la-row"))
            self.page.click("#globalModal .btn-close")                              # close like a user
            self.page.wait_for_selector("#globalModal.show", state="detached", timeout=8000)
            self.ask(SIMILAR, "purchase price already deducts")
            system = prov.calls[-1]["messages"][0]["content"]
            self.assertIn("ANSWERS THE USER APPROVED", system)
            self.assertIn(ANSWER, system)

    def test_thumbs_down_clear_and_reload_state(self):
        with patch(PROVIDER, return_value=stub_provider(reply=ANSWER)):
            self.open_ai()
            self.ask(LAPTOP, "purchase price already deducts")
            self.page.click(".ai-ws-fb-down")
            self.page.wait_for_selector(".ai-ws-fb-down.active", timeout=5000)
            self.assertEqual(AIAnswerFeedback.objects.get(owner=self.user).rating, -1)
            self.page.click(".ai-ws-fb-down")                                       # same thumb again clears it
            self.page.wait_for_function("() => !document.querySelector('.ai-ws-fb-down.active')", timeout=5000)
            self.assertEqual(AIAnswerFeedback.objects.count(), 0)
            self.page.click(".ai-ws-fb-up")
            self.page.wait_for_selector(".ai-ws-fb-up.active", timeout=5000)
            self.page.reload()                                                      # state survives a reload of the conversation
            self.page.wait_for_selector("#ai-ws-input", timeout=15000)
            self.page.click(".ai-ws-conv-item, .ai-ws-history-item, [data-conv-id]", timeout=8000)
            self.page.wait_for_selector(".ai-ws-fb-up.active", timeout=8000)

    def test_model_timeout_shows_retrieved_facts_in_the_ui(self):
        with patch(PROVIDER, return_value=stub_provider(error="timed out")):
            self.open_ai()
            self.ask(LAPTOP, "did not answer in time")
            text = self.page.inner_text(".ai-ws-msg-content >> nth=-1")
            self.assertIn("NOT written as an Expense row", text)
            self.assertEqual(AIAnswerFeedback.objects.count(), 0)
