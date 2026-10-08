"""Real-browser test (Chromium via Playwright): Settings > Billing trial option + Customers table and actions
(suspend/unsuspend, extend trial, invoices mark paid, refund). Skipped without Chromium."""

from __future__ import annotations

import os
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.utils import timezone

from core.authentication.services import AuthWorkflowService
from core.models import AppSettings, Currency, Invoice, Plan, Subscription

User = get_user_model()


class CustomersLiveTests(StaticLiveServerTestCase):
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

    def _open_billing_settings(self):
        admin = User.objects.create_user(username="cl_admin", password="pw123456", is_staff=True, is_superuser=True)
        profile = AuthWorkflowService.get_profile(admin)
        profile.is_sysadmin = True
        profile.onboarding_completed = True
        profile.save()
        plan, _ = Plan.objects.get_or_create(code="cl_plan", defaults={"name": "Live Plan", "sort_order": 1})
        self.user = User.objects.create_user(username="cl_customer", password="pw123456", email="cl@example.test")
        now = timezone.now()
        self.sub = Subscription.objects.create(owner=self.user, plan=plan, status="trialing", trial_end=now + timedelta(days=4))
        cur = Currency.objects.filter(owner=self.user).first() or Currency.objects.create(owner=self.user, code="USD", name="US Dollar", symbol="$")
        make = lambda status: Invoice.objects.create(  # noqa: E731
            owner=self.user, subscription=self.sub, plan=plan, amount=Decimal("50.00"), currency=cur, status=status,
            period_start=now, period_end=now + timedelta(days=30))
        self.pending, self.paid = make("pending"), make("paid")
        self.client.force_login(admin)
        ctx = self._browser.new_context(viewport={"width": 1400, "height": 1000})
        ctx.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                          "url": self.live_server_url}])
        self.addCleanup(ctx.close)
        self.page = ctx.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)[:200]))
        self.page.on("dialog", lambda d: d.accept())
        self.page.goto(f"{self.live_server_url}/#settings-billing")
        self.page.wait_for_selector("#customersTable", timeout=60000)
        self.row = self.page.locator("#customersTable tbody tr", has_text="cl_customer")

    def _until(self, check, what, timeout=10000):
        end = timeout / 250
        for _ in range(int(end)):
            if check():
                return
            self.page.wait_for_timeout(250)
        self.fail(f"timed out waiting for: {what}")

    def _modal(self):
        return self.page.locator("#globalModal.show")

    def test_trial_option_and_customer_actions(self):
        self._open_billing_settings()
        self.assertEqual(self.row.count(), 1)
        self.assertIn("Live Plan", self.row.inner_text())

        box = self.page.locator("#trialOnAdminCreated")
        self.assertTrue(box.is_checked())
        box.uncheck()
        self._until(lambda: AppSettings.get("trial_on_admin_created_users") == "false", "trial option saved off")
        box.check()
        self._until(lambda: AppSettings.get("trial_on_admin_created_users") == "true", "trial option saved on")

        self.row.locator("button[title='Suspend']").click()
        self._until(lambda: Subscription.objects.get(pk=self.sub.pk).status == "suspended", "suspended")
        self.row.locator("button[title='Unsuspend']").click()
        self._until(lambda: Subscription.objects.get(pk=self.sub.pk).status == "trialing", "unsuspended")

        before = Subscription.objects.get(pk=self.sub.pk).trial_end
        self.row.locator("button[title='Extend trial']").click()
        self._modal().locator("#extendTrialDays").wait_for(timeout=10000)
        self._modal().locator("#extendTrialDays").fill("5")
        self._modal().locator("button:has-text('Save')").click()
        self._until(lambda: Subscription.objects.get(pk=self.sub.pk).trial_end == before + timedelta(days=5), "trial extended")
        self.page.wait_for_selector("#globalModal.show", state="detached", timeout=10000)

        self.row.locator("button[title='Invoices']").click()
        self._modal().locator("button:has-text('Mark paid')").wait_for(timeout=10000)
        self._modal().locator("button:has-text('Mark paid')").click()
        self._until(lambda: Invoice.objects.get(pk=self.pending.pk).status == "paid", "invoice marked paid")
        self._modal().locator(f"#refundRow_{self.paid.id}").wait_for(state="attached", timeout=10000)
        self._modal().locator("button:has-text('Refund')").first.click()
        self._modal().locator(f"#refundNote_{self.paid.id}").wait_for(timeout=10000)
        self._modal().locator(f"#refundNote_{self.paid.id}").fill("live test")
        self._modal().locator(f"#refundRow_{self.paid.id} button:has-text('Refund')").click()
        self._until(lambda: Invoice.objects.get(pk=self.paid.pk).status == "refunded", "invoice refunded")
        self.assertEqual(Invoice.objects.get(pk=self.paid.pk).refund_note, "live test")
        self.assertEqual(self.errors, [], f"JS errors: {self.errors}")
