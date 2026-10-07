"""Real-browser test (Chromium via Playwright): the 'Your data' card works for a LAPSED user (locked to the plans
page): export downloads JSON, a wrong confirmation is refused, the full delete flow removes the account.
Skipped without Chromium."""

from __future__ import annotations

import json
import os
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.utils import timezone

from core.models import PagePermission, Plan, Subscription

User = get_user_model()


class AccountDataLiveTests(StaticLiveServerTestCase):
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

    def open_lapsed(self, name):
        plan, _ = Plan.objects.get_or_create(code="acct_live_plan", defaults={"name": "Live", "sort_order": 1})
        user = User.objects.create_user(username=name, password="pw123456")
        Subscription.objects.create(owner=user, plan=plan, status="trialing", trial_end=timezone.now() - timedelta(days=1))
        PagePermission.objects.create(user=user, page="dashboard", granted=True)
        self.client.force_login(user)
        ctx = self._browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        ctx.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                          "url": self.live_server_url}])
        self.addCleanup(ctx.close)
        self.page = ctx.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.goto(f"{self.live_server_url}/#dashboard")
        skip = self.page.locator("#globalModal.show button:has-text('Skip for now')")
        try:
            skip.wait_for(state="visible", timeout=6000)
            skip.click()
            self.page.wait_for_timeout(1500)
        except Exception:
            pass
        self.page.wait_for_function("() => location.hash === '#billing-plans'", timeout=30000)
        self.page.wait_for_selector("#wf-account-data .wf-account-card", timeout=15000)
        return user

    def test_lapsed_user_can_export_then_delete_account(self):
        user = self.open_lapsed("acct_live")
        with self.page.expect_download(timeout=15000) as dl:
            self.page.click("#wf-account-export-btn")
        path = dl.value.path()
        self.assertTrue(dl.value.suggested_filename.endswith(".json"))
        self.assertEqual(json.load(open(path, encoding="utf-8"))["username"], "acct_live")

        self.page.click("#wf-account-delete-btn")
        self.assertTrue(self.page.eval_on_selector("#wf-account-delete-form", "e => !e.hidden"))
        self.page.fill("#wf-account-password", "wrong-password")
        self.page.fill("#wf-account-confirm", "DELETE")
        self.page.click("#wf-account-delete-confirm-btn")
        self.page.wait_for_timeout(1200)
        self.assertTrue(User.objects.filter(pk=user.pk).exists())            # wrong password: nothing deleted

        self.page.fill("#wf-account-password", "pw123456")
        self.page.fill("#wf-account-confirm", "nope")
        self.page.click("#wf-account-delete-confirm-btn")
        self.page.wait_for_timeout(600)
        self.assertTrue(User.objects.filter(pk=user.pk).exists())            # missing DELETE: nothing deleted

        self.page.fill("#wf-account-confirm", "DELETE")
        self.page.click("#wf-account-delete-confirm-btn")
        self.page.wait_for_url("**/accounts/login/**", timeout=15000)
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertEqual(self.errors, [])
