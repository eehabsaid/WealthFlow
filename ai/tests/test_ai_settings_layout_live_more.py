"""AI Advisor layout live tests: more menu, phone overflow and chat domains."""



from django.test import tag

from ai.tests.live_boot import open_ai_tab
from .ai_settings_layout_support import AISettingsLayoutLiveBase, GROUPS, SHOTS


@tag("requires_host_ui")
class AISettingsLayoutLiveMoreTests(AISettingsLayoutLiveBase):
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
