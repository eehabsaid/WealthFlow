"""Real-browser test (Chromium via Playwright) of the Settings > AI Advisor layout: every setting id is still there, each group is
one card, only the chosen section is visible (side nav on wide screens, chip bar on narrow ones), Test Connection ends the Provider
card, Save sits in the sticky bar, and nothing overflows on a phone in light/dark, LTR/RTL. Skipped when Chromium is not installed."""



from django.conf import settings
from django.test import tag

from ai.tests.live_boot import open_ai_tab
from .ai_settings_layout_support import AISettingsLayoutLiveBase, GROUPS, IDS, SHOTS


@tag("requires_host_ui")
class AISettingsLayoutLiveTests(AISettingsLayoutLiveBase):
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
