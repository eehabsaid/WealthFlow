"""Shared browser setup for the AI Advisor layout live tests."""


import os
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from ai.tests.live_boot import PageDiagnostics, first_load, scale_timeouts
from ai.tests.support import grant_ai_workspace_access, make_sysadmin


User = get_user_model()

IDS = ["aiEnabledToggle", "aiProviderSelect", "aiModelInput", "aiTemperatureInput", "aiContextSizeInput", "aiTimeoutInput",
       "aiRuntimeCapabilitiesBtn", "aiAdvancedAccordion", "aiSystemPromptInput", "aiMaxTokensInput", "aiTopPInput", "aiTopKInput",
       "aiRepeatPenaltyInput", "aiSeedInput", "aiKeepAliveInput", "aiTestConnBtn", "aiTestDiagnosticResult",
       "aiDomainBusinessToggle", "aiDomainAppToggle", "aiPermissionTierSelect", "aiCodeAccessToggle", "aiValidateModeSelect", "aiDirectAnswersToggle", "aiMultiAgentToggle",
       "aiInvestigatorModeSelect", "aiAgentEnabledToggle", "aiAgentInstructionsInput", "aiAgentInstructionsResetBtn",
       "aiAgentMaxStepsInput", "aiAgentBudgetInput", "aiAgentMaxReadsInput", "aiDocumentBudgetInput", "aiDocumentMaxTokensInput",
       "aiDocumentInstructionsInput", "aiDocumentInstructionsResetBtn", "aiFileGenerationToggle", "aiFileMaxMbInput",
       "aiFileMaxRowsInput", "aiPipelineDebugToggle", "aiSaveBtn", "aiUserLimitsPanel",
       "speech_stt_enabled", "speech_stt_endpoint", "speech_stt_test", "speech_tts_enabled", "speech_tts_endpoint", "speech_tts_test",
       "speech_tts_ar_enabled", "speech_tts_ar_endpoint", "speech_tts_ar_test",
       "image_gen_enabled", "image_gen_provider", "image_gen_model", "image_gen_endpoint", "image_gen_api_key", "image_gen_start_command", "image_gen_test"]
GROUPS = ["provider", "safety", "domains", "routing", "agent", "docs", "files", "speech", "image", "diag"]
SHOTS = os.environ.get("AI_LAYOUT_SHOTS", "")


class AISettingsLayoutLiveBase(StaticLiveServerTestCase):
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

    def open(self, width, height, theme="dark", rtl=False, route="settings-aiadvisor", ready="#aiSaveBtn"):
        admin = User.objects.create_user(username=f"lay_admin_{uuid.uuid4().hex[:10]}", password="pw123456", is_staff=True)
        make_sysadmin(admin)
        grant_ai_workspace_access(admin)
        self.client.force_login(admin)
        ctx = self._browser.new_context(viewport={"width": width, "height": height})
        ctx.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                          "url": self.live_server_url}])
        scale_timeouts(ctx)
        self.addCleanup(ctx.close)
        page = ctx.new_page()
        PageDiagnostics(page)
        first_load(page, f"{self.live_server_url}/#{route}")
        if route not in page.url:
            page.goto(f"{self.live_server_url}/#{route}", wait_until="domcontentloaded")
        page.wait_for_selector(ready, state="attached", timeout=60000)
        page.wait_for_load_state("networkidle")
        page.evaluate("([t, r]) => { document.documentElement.setAttribute('data-theme', t); document.body.setAttribute('data-theme', t); if (r) document.documentElement.dir = 'rtl'; }", [theme, rtl])
        return page
