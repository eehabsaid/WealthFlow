"""Real-browser sweep (Chromium via Playwright): every Settings tab must render and the page must raise no
JavaScript error. Guards against a script tag going missing from a template (e.g. renderLegalSettings undefined
blanked every Settings tab). Skipped when Chromium is not installed."""

from __future__ import annotations

import os
import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from core.authentication.services import AuthWorkflowService

TABS_JS = Path(settings.BASE_DIR) / "static/js/settings/tabs.js"


class SettingsTabsLiveTests(StaticLiveServerTestCase):
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

    def test_every_settings_tab_renders_without_js_errors(self):
        admin = get_user_model().objects.create_user(username="tabs_admin", password="pw123456", is_staff=True, is_superuser=True)
        profile = AuthWorkflowService.get_profile(admin)
        profile.is_sysadmin = True
        profile.onboarding_completed = True
        profile.save()
        self.client.force_login(admin)
        ctx = self._browser.new_context(viewport={"width": 1400, "height": 1000})
        ctx.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                          "url": self.live_server_url}])
        self.addCleanup(ctx.close)
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))
        routes = re.findall(r'route:\s*"(settings-[a-z]+)"', TABS_JS.read_text())
        self.assertGreater(len(routes), 15)
        page.goto(f"{self.live_server_url}/#{routes[0]}")
        page.wait_for_selector("#settingsContent", timeout=60000)
        blank = []
        for route in routes:
            page.evaluate("(r) => { window.location.hash = r; }", route)
            page.wait_for_timeout(1200)
            text = page.evaluate("() => (document.getElementById('settingsContent') || {}).innerText || ''")
            if len(text.strip()) < 5:
                blank.append(route)
        self.assertEqual(errors, [], f"JS errors while opening Settings tabs: {errors}")
        self.assertEqual(blank, [], f"Settings tabs rendered blank: {blank}")
