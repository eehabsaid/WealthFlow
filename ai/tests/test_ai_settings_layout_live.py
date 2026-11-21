"""Real-browser test (Chromium via Playwright) of the Settings > AI Advisor layout: every setting id is still there, each group is
one card, only the chosen section is visible (side nav on wide screens, chip bar on narrow ones), Test Connection ends the Provider
card, Save sits in the sticky bar, and nothing overflows on a phone in light/dark, LTR/RTL. Skipped when Chromium is not installed."""

from __future__ import annotations

import os
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag

from ai.tests.live_boot import PageDiagnostics, first_load, open_ai_tab, scale_timeouts
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


@tag("requires_host_ui")
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

    def test_every_setting_is_still_there_in_ten_cards_with_test_connection_in_the_provider_card(self):
        p = self.open(1400, 1000)
        self.assertEqual([i for i in IDS if p.locator(f"#{i}").count() != 1], [])
        self.assertEqual(p.locator(".aia-card").count(), len(GROUPS))
        self.assertEqual(p.locator("#aiaGroup-provider #aiTestConnBtn").count(), 1)
        self.assertEqual(p.locator("#aiaGroup-provider #aiTestDiagnosticResult").count(), 1)
        self.assertEqual(p.locator(".aia-savebar #aiSaveBtn").count(), 1)
        self.assertEqual(p.locator(".aia-chip").count(), len(GROUPS) + 1)   # the groups + "Usage limits" (shown once the sysadmin panel loaded)
        self.assertEqual(p.locator(".aia-card:visible").count(), 1)          # one section at a time ...
        self.assertTrue(p.is_visible("#aiaGroup-provider"))                  # ... starting with Provider and model
        self.assertEqual(p.locator("#aiaGroup-agent input[type=number]").count(), 3)
        self.assertEqual(p.locator("#aiaGroup-docs input[type=number]").count(), 2)
        self.assertEqual(p.locator("#aiaGroup-files input[type=number]").count(), 2)
        self.assertEqual(p.locator("#aiaGroup-speech input[type=number]").count(), 3)   # STT, TTS and Arabic-voice timeouts
        self.assertEqual(p.locator("#aiaGroup-speech #speech_stt_test, #aiaGroup-speech #speech_tts_test, #aiaGroup-speech #speech_tts_ar_test").count(), 3)
        self.assertEqual(p.locator("#aiaGroup-image [id^=image_gen_]").count(), 8)   # switch, provider, model, URL, key, start command, test button, test result
        self.assertEqual(p.locator("#aiaGroup-provider [id^=speech_], #aiaGroup-provider [id^=image_gen_]").count(), 0)
        # Test Connection is the last control of the Provider card
        last = p.evaluate("() => [...document.querySelectorAll('#aiaGroup-provider button')].pop().id")
        self.assertEqual(last, "aiTestConnBtn")
        if SHOTS:
            p.screenshot(path=f"{SHOTS}/desktop_dark.png", full_page=True)

    def test_a_tab_shows_only_its_section_without_changing_the_route(self):
        p = self.open(1400, 900)
        open_ai_tab(p, "files")
        self.assertTrue(p.is_visible("#aiaGroup-files"))
        self.assertTrue(p.is_hidden("#aiaGroup-provider"))
        self.assertEqual(p.locator(".aia-card:visible").count(), 1)
        self.assertIn("settings-aiadvisor", p.url)
        self.assertEqual(p.locator(".aia-chip.active").count(), 1)
        self.assertEqual(p.get_attribute('.aia-chip.active', "data-aia-target"), "files")
        # a hidden section keeps its values: Save sends every group no matter which one is open
        open_ai_tab(p, "provider")
        p.fill("#aiTemperatureInput", "0.35")
        open_ai_tab(p, "agent")
        self.assertEqual(p.input_value("#aiTemperatureInput"), "0.35")
        # arrow keys move between sections
        p.focus('.aia-chip.active')
        p.keyboard.press("ArrowRight")
        self.assertEqual(p.get_attribute('.aia-chip.active', "data-aia-target"), "docs")

    def test_the_documentation_capture_shows_one_section_at_a_time(self):
        import re
        from pathlib import Path

        from ai.doc_engine.playwright_engine.capture_runner.ai_sections import SECTIONS_JS

        src = Path(settings.BASE_DIR, "ai/doc_engine/playwright_engine/capture_runner/capture.py").read_text(encoding="utf-8")
        css = re.search(r'add_style_tag\(content="""(.*?)"""\)', src, re.S).group(1)   # the stylesheet the screenshot runner injects
        p = self.open(1400, 900)
        p.add_style_tag(content=css)
        self.assertEqual(p.locator(".aia-card:visible").count(), 1)   # the capture no longer stacks the sections
        self.assertEqual(p.locator(".aia-chips:visible").count(), 1)
        info = p.evaluate(SECTIONS_JS)   # the runner photographs each section the page lists, one after the other
        self.assertEqual([x["id"] for x in info["sections"]][:len(GROUPS)], GROUPS)
        for group in GROUPS:
            self.assertTrue(p.evaluate("(id) => window.AIA.ui.showGroup(id)", group))
            self.assertEqual(p.locator(".aia-card:visible").count(), 1)

    def test_the_open_section_survives_save(self):
        p = self.open(1400, 900)
        open_ai_tab(p, "routing")
        p.evaluate("() => { window.__before = document.getElementById('aiaGroup-routing'); }")
        with p.expect_response(lambda r: "/api/settings/ai/" in r.url and r.request.method == "POST"):
            p.click("#aiSaveBtn")
        # Save re-renders the page: wait for the new DOM, then the section that was open must still be the visible one
        p.wait_for_function("() => { const n = document.getElementById('aiaGroup-routing'); return n && n !== window.__before; }")
        self.assertTrue(p.is_visible("#aiaGroup-routing"))
        self.assertEqual(p.locator(".aia-card:visible").count(), 1)
        self.assertEqual(p.get_attribute('.aia-chip.active', "data-aia-target"), "routing")

    def test_the_tabs_sit_on_top_and_never_stretch_the_page(self):
        # the app already has a sidebar, so the sections are a tab bar under the title at every width
        for width in (1400, 820, 390):
            p = self.open(width, 900)
            self.assertEqual(p.evaluate("() => getComputedStyle(document.getElementById('aiaChips')).flexDirection"), "row")
            tabs, detail = (p.locator(s).bounding_box() for s in ("#aiaChips", "#aiaDetail"))
            self.assertLess(tabs["y"], detail["y"])                                   # tabs above the section, not beside it
            self.assertLessEqual(detail["x"] + detail["width"], width + 1)            # the tab bar must not stretch the page past the screen
            self.assertLessEqual(tabs["x"] + tabs["width"], width + 1)
            self.assertLessEqual(p.evaluate("() => { const n = document.getElementById('aiaChips'); return n.scrollWidth - n.clientWidth; }"), 1)

    def test_tabs_that_do_not_fit_move_into_a_more_menu(self):
        bar = "() => [...document.querySelectorAll('#aiaChips > .aia-chip:not([hidden])')].map(c => c.dataset.aiaTarget)"
        menu = "() => [...document.querySelectorAll('.aia-more-menu .aia-chip')].map(c => c.dataset.aiaTarget)"
        p = self.open(1400, 900)
        wide = len(p.evaluate(bar))
        p.set_viewport_size({"width": 390, "height": 800})
        p.wait_for_function("(n) => document.querySelectorAll('#aiaChips > .aia-chip:not([hidden])').length < n", arg=wide)   # re-laid out
        narrow_bar, narrow_menu = p.evaluate(bar), p.evaluate(menu)
        self.assertLess(len(narrow_bar), wide)
        self.assertTrue(narrow_menu)                                                  # the hidden tabs are in the menu ...
        self.assertEqual(len(narrow_bar) + len(narrow_menu), p.locator('.aia-chip:not([hidden])').count())   # ... and none is lost
        self.assertTrue(p.is_hidden(".aia-more-menu"))
        p.click(".aia-more-btn")
        self.assertTrue(p.is_visible(".aia-more-menu"))
        box = p.locator(".aia-more-menu").bounding_box()
        self.assertTrue(0 <= box["x"] and box["x"] + box["width"] <= 391)             # the dropdown stays on screen
        target = narrow_menu[-1]
        p.click(f'.aia-more-menu .aia-chip[data-aia-target="{target}"]')
        self.assertTrue(p.is_visible(f"#aiaGroup-{target}"))
        self.assertTrue(p.is_hidden(".aia-more-menu"))                                # picking a tab closes the menu
        self.assertIn("active", p.get_attribute(".aia-more-btn", "class"))            # More shows that its tab is the open one
        p.click(".aia-more-btn")
        p.keyboard.press("Escape")
        self.assertTrue(p.is_hidden(".aia-more-menu"))
        p.set_viewport_size({"width": 1400, "height": 900})                           # widening moves tabs back into the bar
        p.wait_for_function("(n) => document.querySelectorAll('#aiaChips > .aia-chip:not([hidden])').length > n", arg=len(narrow_bar))

    def test_nothing_overflows_on_a_phone_in_light_theme_and_in_rtl(self):
        for theme, rtl in (("light", False), ("dark", True)):
            p = self.open(390, 800, theme=theme, rtl=rtl)
            for group in GROUPS:                       # every section is checked: a hidden one has no width to measure
                open_ai_tab(p, group)
                self.assertLessEqual(p.evaluate("() => document.documentElement.scrollWidth"), 392, f"{group} {theme} rtl={rtl}")
                rows = p.evaluate("() => [...document.querySelectorAll('.aia-card:not([hidden]) .aia-row')].filter(r => r.scrollWidth > r.clientWidth + 1).map(r => (r.querySelector('label')||{}).htmlFor)")
                self.assertEqual(rows, [], f"{group} {theme} rtl={rtl}")
            if SHOTS:
                p.screenshot(path=f"{SHOTS}/mobile_{theme}_{'rtl' if rtl else 'ltr'}.png", full_page=True)

    def test_the_workspace_dropdown_follows_the_chat_domains_the_sysadmin_allows(self):
        from ai.models import AISetting

        for business, app, visible in ((True, True, True), (True, False, False), (False, True, False)):
            AISetting.set("ai_domain_business", "true" if business else "false", user=None)
            AISetting.set("ai_domain_app", "true" if app else "false", user=None)
            p = self.open(1300, 900, route="ai", ready="#ai-ws-domain-select")
            p.wait_for_function("() => Array.isArray(_aiState.domains)", timeout=30000)
            self.assertEqual(p.evaluate("() => document.getElementById('ai-ws-domain-select').hidden"), not visible, (business, app))
            if not visible:
                expected = "business_data_analysis" if business else "app_features_architecture"
                self.assertEqual(p.evaluate("() => document.getElementById('ai-ws-domain-select').value"), expected)

    def test_the_settings_card_keeps_one_domain_checked(self):
        p = self.open(1300, 900)
        open_ai_tab(p, "domains")
        p.uncheck("#aiDomainAppToggle")
        p.click("#aiDomainBusinessToggle")          # the last one cannot be switched off: the page checks it again
        self.assertTrue(p.is_checked("#aiDomainBusinessToggle"))
        self.assertFalse(p.is_checked("#aiDomainAppToggle"))
