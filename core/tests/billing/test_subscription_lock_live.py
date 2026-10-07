"""Real-browser test (Chromium via Playwright): once a trial/subscription lapses the app is locked to the upgrade
page (banner + router lock + 402 on the data API); an active user is untouched. Skipped without Chromium."""

from __future__ import annotations

import os
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.utils import timezone

from core.models import PagePermission, Plan, Subscription

User = get_user_model()


class SubscriptionLockLiveTests(StaticLiveServerTestCase):
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

    def open_as(self, name, status, trial_end=None):
        plan, _ = Plan.objects.get_or_create(code="lock_plan", defaults={"name": "Lock", "sort_order": 1})
        user = User.objects.create_user(username=name, password="pw123456")
        Subscription.objects.create(owner=user, plan=plan, status=status, trial_end=trial_end,
                                    current_period_end=timezone.now() + timedelta(days=30) if status == "active" else None)
        for page in ("dashboard", "balance", "banks"):                 # permissions are NOT what locks the lapsed user
            PagePermission.objects.create(user=user, page=page, granted=True)
        self.client.force_login(user)
        ctx = self._browser.new_context(viewport={"width": 1280, "height": 900})
        ctx.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                          "url": self.live_server_url}])
        self.addCleanup(ctx.close)
        self.page = ctx.new_page()
        self.page.goto(f"{self.live_server_url}/#balance")
        skip = self.page.locator("#globalModal.show button:has-text('Skip for now')")
        try:
            skip.wait_for(state="visible", timeout=6000)
            skip.click()
            self.page.wait_for_timeout(1500)
        except Exception:
            pass

    def hash(self):
        return self.page.evaluate("() => location.hash")

    def status_of(self, path):
        return self.page.evaluate("async (p) => (await fetch(p)).status", path)

    def test_expired_trial_is_locked_to_the_upgrade_page(self):
        self.open_as("lock_expired", "trialing", timezone.now() - timedelta(days=1))
        self.page.wait_for_function("() => location.hash === '#billing-plans'", timeout=30000)
        self.page.wait_for_selector("#trial-banner-mount .wf-billing-banner-expired", timeout=15000)
        self.assertIn("trial has ended", self.page.inner_text("#trial-banner-mount"))
        for route in ("#dashboard", "#balance", "#banks"):            # every other page bounces back to upgrade
            self.page.evaluate("(r) => { location.hash = r; }", route)
            self.page.wait_for_function("() => location.hash === '#billing-plans'", timeout=10000)
        self.assertEqual(self.status_of("/api/balance/"), 402)         # server-side lock, not just UI
        self.assertEqual(self.status_of("/api/banks/"), 402)
        self.assertEqual(self.status_of("/api/billing/plans/"), 200)   # upgrade page still works
        self.assertEqual(self.status_of("/api/billing/status/"), 200)

    def test_active_subscription_is_not_locked(self):
        self.open_as("lock_active", "active")
        self.page.wait_for_function("() => location.hash === '#balance'", timeout=30000)
        self.page.wait_for_timeout(2500)                               # a late billing-status reply must not lock
        self.assertEqual(self.hash(), "#balance")
        self.assertNotEqual(self.status_of("/api/balance/"), 402)
        self.assertEqual(self.page.locator("#trial-banner-mount .wf-billing-banner-expired").count(), 0)
