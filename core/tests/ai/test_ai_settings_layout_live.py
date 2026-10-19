"""Real-browser test (Chromium via Playwright) of the Settings > AI Advisor layout: every setting id is still there, each group is
one card, Test Connection ends the Provider card, Save sits in the sticky bar, and nothing overflows on a phone. Skipped when
Chromium is not installed."""

from __future__ import annotations

import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from core.authentication.services import AuthWorkflowService
from core.tests.ai.live_boot import PageDiagnostics, first_load, scale_timeouts
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()

IDS = ["aiEnabledToggle", "aiProviderSelect", "aiModelInput", "aiTemperatureInput", "aiContextSizeInput", "aiTimeoutInput",
       "aiRuntimeCapabilitiesBtn", "aiAdvancedAccordion", "aiSystemPromptInput", "aiMaxTokensInput", "aiTopPInput", "aiTopKInput",
       "aiRepeatPenaltyInput", "aiSeedInput", "aiKeepAliveInput", "aiTestConnBtn", "aiTestDiagnosticResult",
       "aiPermissionTierSelect", "aiCodeAccessToggle", "aiValidateModeSelect", "aiDirectAnswersToggle", "aiMultiAgentToggle",
       "aiInvestigatorModeSelect", "aiAgentEnabledToggle", "aiAgentInstructionsInput", "aiAgentInstructionsResetBtn",
       "aiAgentMaxStepsInput", "aiAgentBudgetInput", "aiAgentMaxReadsInput", "aiDocumentBudgetInput", "aiDocumentMaxTokensInput",
       "aiDocumentInstructionsInput", "aiDocumentInstructionsResetBtn", "aiFileGenerationToggle", "aiFileMaxMbInput",
       "aiFileMaxRowsInput", "aiPipelineDebugToggle", "aiSaveBtn", "aiUserLimitsPanel"]
GROUPS = ["provider", "safety", "routing", "agent", "docs", "files", "diag"]
SHOTS = os.environ.get("AI_LAYOUT_SHOTS", "")


class AISettingsLayoutLiveTests(StaticLiveServerTestCase):
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

    def open(self, width, height, theme="dark", rtl=False):
        admin = User.objects.create_user(username=f"lay_admin_{width}_{theme}_{int(rtl)}", password="pw123456", is_staff=True)
        profile = AuthWorkflowService.get_profile(admin)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        grant_ai_workspace_access(admin)
        self.client.force_login(admin)
        ctx = self._browser.new_context(viewport={"width": width, "height": height})
        ctx.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                          "url": self.live_server_url}])
        scale_timeouts(ctx)
        self.addCleanup(ctx.close)
        page = ctx.new_page()
        PageDiagnostics(page)
        first_load(page, f"{self.live_server_url}/#settings-aiadvisor")
        if "settings-aiadvisor" not in page.url:
            page.goto(f"{self.live_server_url}/#settings-aiadvisor", wait_until="domcontentloaded")
        page.wait_for_selector("#aiSaveBtn", timeout=60000)
        page.evaluate("([t, r]) => { document.documentElement.setAttribute('data-theme', t); document.body.setAttribute('data-theme', t); if (r) document.documentElement.dir = 'rtl'; }", [theme, rtl])
        return page

    def test_every_setting_is_still_there_in_seven_cards_with_test_connection_in_the_provider_card(self):
        p = self.open(1400, 1000)
        self.assertEqual([i for i in IDS if p.locator(f"#{i}").count() != 1], [])
        self.assertEqual(p.locator(".aia-card").count(), len(GROUPS))
        self.assertEqual(p.locator("#aiaGroup-provider #aiTestConnBtn").count(), 1)
        self.assertEqual(p.locator("#aiaGroup-provider #aiTestDiagnosticResult").count(), 1)
        self.assertEqual(p.locator(".aia-savebar #aiSaveBtn").count(), 1)
        self.assertEqual(p.locator(".aia-chip").count(), len(GROUPS))
        self.assertEqual(p.locator("#aiaGroup-agent input[type=number]").count(), 3)
        self.assertEqual(p.locator("#aiaGroup-docs input[type=number]").count(), 2)
        self.assertEqual(p.locator("#aiaGroup-files input[type=number]").count(), 2)
        # Test Connection is the last control of the Provider card
        last = p.evaluate("() => [...document.querySelectorAll('#aiaGroup-provider button')].pop().id")
        self.assertEqual(last, "aiTestConnBtn")
        if SHOTS:
            p.screenshot(path=f"{SHOTS}/desktop_dark.png", full_page=True)

    def test_a_chip_scrolls_to_its_card_without_changing_the_route(self):
        p = self.open(1400, 900)
        p.click('.aia-chip[data-aia-target="files"]')
        p.wait_for_function("() => document.getElementById('aiaGroup-files').getBoundingClientRect().top < 400")
        self.assertIn("settings-aiadvisor", p.url)
        self.assertEqual(p.locator(".aia-chip.active").count(), 1)

    def test_nothing_overflows_on_a_phone_in_light_theme_and_in_rtl(self):
        for theme, rtl in (("light", False), ("dark", True)):
            p = self.open(390, 800, theme=theme, rtl=rtl)
            self.assertLessEqual(p.evaluate("() => document.documentElement.scrollWidth"), 392, f"{theme} rtl={rtl}")
            rows = p.evaluate("() => [...document.querySelectorAll('.aia-row')].filter(r => r.scrollWidth > r.clientWidth + 1).map(r => (r.querySelector('label')||{}).htmlFor)")
            self.assertEqual(rows, [], f"{theme} rtl={rtl}")
            if SHOTS:
                p.screenshot(path=f"{SHOTS}/mobile_{theme}_{'rtl' if rtl else 'ltr'}.png", full_page=True)
