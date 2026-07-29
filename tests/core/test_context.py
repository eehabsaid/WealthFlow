"""
WealthFlow Test Context & Browser Control Manager
Provides Playwright browser context, authentication, viewports (desktop/tablet/mobile),
theme switching (dark/light), language switching (en/ar/fr/de), console/network log listening,
and browser navigation controls (reload, back/forward, keyboard nav).
"""

import os
import json
import time

class TestContext:
    def __init__(self, playwright, headed=False, slow_mo=150, device="desktop"):
        self.playwright = playwright
        self.headed = headed
        self.slow_mo = slow_mo
        self.device = device
        
        # Viewport mappings
        self.viewports = {
            "desktop": {"width": 1440, "height": 900},
            "tablet": {"width": 768, "height": 1024},
            "mobile": {"width": 375, "height": 812},
        }

        self.console_errors = []
        self.console_warnings = []
        self.page_exceptions = []
        self.failed_http_responses = []

        self._launch_browser()

    def _launch_browser(self):
        vp = self.viewports.get(self.device, self.viewports["desktop"])
        is_mobile = (self.device == "mobile")
        
        self.browser = self.playwright.chromium.launch(
            headless=not self.headed,
            slow_mo=self.slow_mo
        )
        self.context = self.browser.new_context(
            viewport=vp,
            is_mobile=is_mobile,
            accept_downloads=True
        )
        self.page = self.context.new_page()

        # Listeners
        def on_console(msg):
            text = msg.text
            if "favicon" in text or "font" in text or "status of 400" in text or "status of 401" in text:
                return
            if msg.type == "error":
                self.console_errors.append(f"[CONSOLE ERROR] {text}")
            elif msg.type == "warning":
                self.console_warnings.append(f"[CONSOLE WARN] {text}")

        def on_page_error(err):
            self.page_exceptions.append(f"[UNCAUGHT EXCEPTION] {err.message}\nStack: {err.stack}")

        def on_response(response):
            if response.status >= 500:
                self.failed_http_responses.append(f"HTTP {response.status} (Server Error): {response.url}")

        self.page.on("console", on_console)
        self.page.on("pageerror", on_page_error)
        self.page.on("response", on_response)

    def login(self, username="eehab_said", password="Eehabdev1", base_url="http://127.0.0.1:8000"):
        res = self.context.request.post(
            f"{base_url}/api/auth/login/",
            data=json.dumps({"username": username, "password": password}),
            headers={"Content-Type": "application/json"}
        )
        self.page.goto(f"{base_url}/")
        self.page.wait_for_timeout(1000)
        return res.status == 200

    def goto_route(self, hash_route, base_url="http://127.0.0.1:8000"):
        url = f"{base_url}/{hash_route}"
        self.page.goto(url)
        self.page.wait_for_timeout(800)

    def set_theme(self, theme="dark"):
        """Switches UI Theme ('dark' or 'light')."""
        self.page.evaluate(f"""(th) => {{
            if (typeof toggleTheme === 'function') {{
                const current = document.documentElement.getAttribute('data-bs-theme') || 'dark';
                if (current !== th) toggleTheme();
            }}
        }}""", theme)
        self.page.wait_for_timeout(500)

    def set_language(self, lang="en"):
        """Switches active application language ('en', 'ar', 'fr', 'de')."""
        self.page.evaluate(f"""(l) => {{
            if (typeof loadLanguage === 'function') loadLanguage(l);
        }}""", lang)
        self.page.wait_for_timeout(800)

    def reload(self):
        """Refreshes the current page."""
        self.page.reload()
        self.page.wait_for_timeout(800)

    def go_back(self):
        """Browser Back button action."""
        self.page.go_back()
        self.page.wait_for_timeout(800)

    def go_forward(self):
        """Browser Forward button action."""
        self.page.go_forward()
        self.page.wait_for_timeout(800)

    def close(self):
        try:
            self.browser.close()
        except Exception:
            pass
