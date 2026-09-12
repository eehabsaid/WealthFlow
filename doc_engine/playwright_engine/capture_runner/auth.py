"""AuthMixin: retry wrapper and login flow. See this package's __init__.py
for the sibling list and composition conventions."""
import time
from typing import Any

from playwright.sync_api import Page

from .helpers import log


class AuthMixin:
    def execute_with_retry(self, action_name: str, action_fn) -> Any:
        try:
            return action_fn()
        except Exception as err:
            log(f"Retry 1 for {action_name} due to error: {err}")
            time.sleep(2.0)
            return action_fn()

    def perform_login(self, page: Page) -> None:
        log("Capturing Auth Pages...")
        self.global_context["page_id"] = "auth"
        self.global_context["route"] = "auth"

        page.goto(f"{self.base_url}/accounts/signup/")
        self.wait_for_ui_ready(page)
        page.wait_for_timeout(500)
        self.global_context["tab_id"] = "create_account"
        self.global_context["page_title"] = "Create Account"
        self.capture_screenshot(page, "create_account")

        page.goto(f"{self.base_url}/accounts/forgot-password/")
        self.wait_for_ui_ready(page)
        page.wait_for_timeout(500)
        self.global_context["tab_id"] = "forgot_password"
        self.global_context["page_title"] = "Forgot Password"
        self.capture_screenshot(page, "forgot_password")

        page.goto(f"{self.base_url}/accounts/login/")
        self.wait_for_ui_ready(page)
        page.wait_for_timeout(500)
        self.global_context["tab_id"] = "login"
        self.global_context["page_title"] = "Login"
        self.capture_screenshot(page, "login")

        self.global_context["tab_id"] = None
        self.global_context["route"] = None
        self.global_context["page_id"] = None

        log(f"Logging in at {self.base_url}...")
        page.fill('input[name="username"], input[type="email"]', self.username)
        page.fill('input[name="password"], input[type="password"]', self.password)
        page.click('button[type="submit"], input[type="submit"], .btn-login')
        self.wait_for_ui_ready(page)

