"""Real-browser test (Chromium via Playwright, stub model, real UI and server) of per-user AI settings and the
sysadmin monthly token limit, from a plain Member's point of view. Skipped when Chromium is not installed."""

from __future__ import annotations

import os
from unittest.mock import patch

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.cache import cache

from core.constants.ai_user_settings import DEFAULT_LIMIT_KEY, USE_GENERAL_KEY
from core.models import AIConversation, AIMessage, AppSettings, PagePermission
from core.tests.ai import qe_fixtures as fx
from core.tests.ai.test_ai_workflow_chat import LAPTOP, PROVIDER, stub_provider

ANSWER = "Record it as an asset: the purchase price already deducts your balance."


class AIUserSettingsLiveTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        super().setUpClass()
        try:
            from playwright.sync_api import sync_playwright

            cls._pw = sync_playwright().start()
            cls._browser = cls._pw.chromium.launch(headless=True, args=["--no-sandbox"])
        except Exception as exc:
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
        for page in ("wealthflow_ai", "settings", "settings_myai"):
            PagePermission.objects.create(user=self.user, page=page, granted=True)
        AppSettings.set("ai_direct_answers", "false")
        self.client.force_login(self.user)
        ctx = self._browser.new_context(viewport={"width": 1280, "height": 900})
        ctx.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                          "url": self.live_server_url}])
        self.page = ctx.new_page()
        self.addCleanup(ctx.close)

    def skip_onboarding(self):
        skip = self.page.locator("#globalModal.show button:has-text('Skip for now')")
        try:
            skip.wait_for(state="visible", timeout=6000)
        except Exception:
            return
        skip.click()
        self.page.wait_for_selector("#globalModal.show", state="detached", timeout=8000)

    def open(self, route, selector):
        self.page.goto(f"{self.live_server_url}/#{route}")
        self.skip_onboarding()
        if route not in self.page.url:
            self.page.goto(f"{self.live_server_url}/#{route}")
        self.page.wait_for_selector(selector, timeout=30000)

    def ask(self, text, expect):
        bubbles = self.page.locator(".ai-ws-msg-content").count()
        self.page.fill("#ai-ws-input", text)
        self.page.press("#ai-ws-input", "Enter")
        self.page.wait_for_function("([s, n]) => document.querySelectorAll(s).length > n",
                                    arg=[".ai-ws-msg-content", bubbles + 1], timeout=20000)
        self.page.wait_for_selector(f".ai-ws-msg-content:has-text('{expect}')", timeout=20000)

    def test_member_tab_has_no_sysadmin_fields_and_saves_own_settings(self):
        self.open("settings-myai", "#myAIUseGeneral")
        self.assertTrue(self.page.is_checked("#myAIUseGeneral"))
        self.assertTrue(self.page.eval_on_selector("#myAIOwn", "el => el.disabled"))
        for banned in ("ai_permission_tier", "ai_read_only", "ai_ollama_url", "ai_openai_base_url", "ai_azure_endpoint"):
            self.assertEqual(self.page.locator(f"#{banned}").count(), 0, banned)
        self.assertEqual(self.page.locator(".wf-tab:has-text('AI Advisor')").count(), 0)   # sysadmin tab hidden
        self.assertEqual(self.client.get("/api/settings/ai/").status_code, 403)

        self.page.click("#myAIUseGeneral")
        self.page.select_option("#ai_provider", "ollama")
        self.page.uncheck("#ai_enabled")
        self.page.fill("#ai_model", "my-own-model")
        with self.page.expect_response(lambda r: "/api/settings/ai/me/" in r.url and r.request.method == "POST"):
            self.page.click("#myAISaveBtn")
        self.page.wait_for_selector("#myAIUseGeneral", timeout=10000)
        self.assertEqual(AppSettings.get(USE_GENERAL_KEY, user=self.user), "false")
        self.assertEqual(AppSettings.get("ai_model", user=self.user), "my-own-model")
        self.assertEqual(AppSettings.get("ai_model", user=self.other), AppSettings.get("ai_model"))   # others unaffected
        self.assertFalse(AppSettings.objects.filter(owner=self.user, key__in=["ai_permission_tier", "ai_ollama_url"]).exists())

    def test_limit_blocks_chat_on_general_and_not_on_own_settings(self):
        AppSettings.set(DEFAULT_LIMIT_KEY, "100")
        conv = AIConversation.objects.create(user=self.user)
        AIMessage.objects.create(conversation=conv, role="assistant", content="old", prompt_tokens=140, completion_tokens=10)
        prov = stub_provider(reply=ANSWER)
        with patch(PROVIDER, return_value=prov):
            self.open("ai", "#ai-ws-input")
            self.ask(LAPTOP, "monthly AI token limit")
            self.assertEqual(prov.calls, [])                                   # no model call was made

            AppSettings.set(USE_GENERAL_KEY, "false", user=self.user)          # switched to own settings => unlimited
            self.page.reload()
            self.page.wait_for_selector("#ai-ws-input", timeout=15000)
            self.ask(LAPTOP, "purchase price already deducts")
            self.assertTrue(prov.calls)
        latest = AIMessage.objects.filter(conversation__user=self.user, content__contains="purchase price").first()
        self.assertEqual((latest.prompt_tokens, latest.completion_tokens), (1, 1))   # real usage stamped

    def test_usage_banner_shows_on_general(self):
        AppSettings.set(DEFAULT_LIMIT_KEY, "1000")
        conv = AIConversation.objects.create(user=self.user)
        AIMessage.objects.create(conversation=conv, role="assistant", content="x", prompt_tokens=200, completion_tokens=50)
        self.open("settings-myai", "#myAIUsage")
        text = self.page.inner_text("#myAIUsage")
        self.assertIn("250", text)
        self.assertIn("1,000", text)
