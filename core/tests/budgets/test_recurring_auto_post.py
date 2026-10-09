"""Recurring auto-post on login: per-user setting, default OFF, reuses preview_due/process_due."""

from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from core.models import AppSettings, BalanceEntry, Currency, Expense, RecurringTransaction
from core.services.budgets.auto_post import AUTO_POST_KEY, auto_post_on_login, is_auto_post_enabled

User = get_user_model()
PW = "Pass12345!"


class AutoPostBase(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="rec_login", password=PW)
        self.egp = Currency.objects.create(code="EGP", symbol="EGP", name="Egyptian Pound")
        BalanceEntry.objects.create(owner=self.user, title="Cash (EGP)", balance_type=BalanceEntry.BalanceType.CASH, bank=None, currency=self.egp, amount=10000)
        past = date.today() - timedelta(days=2)
        self.rec = RecurringTransaction.objects.create(
            owner=self.user, name="Netflix", amount=200, currency=self.egp, payment_method="Cash",
            frequency="monthly", interval=1, start_date=past, next_run_date=past)

    def posted(self):
        return Expense.objects.filter(owner=self.user).count()


class AutoPostServiceTests(AutoPostBase):
    def test_default_is_off_and_nothing_is_posted(self):
        self.assertFalse(is_auto_post_enabled(self.user))
        self.assertEqual(auto_post_on_login(self.user), 0)
        self.assertEqual(self.posted(), 0)

    def test_enabled_posts_due_items_once(self):
        AppSettings.set(AUTO_POST_KEY, "true", user=self.user)
        self.assertEqual(auto_post_on_login(self.user), 1)
        self.assertEqual(self.posted(), 1)
        self.assertEqual(auto_post_on_login(self.user), 0)  # next run moved to the future
        self.assertEqual(self.posted(), 1)

    def test_setting_is_per_user(self):
        other = User.objects.create_user(username="someone_else", password=PW)
        AppSettings.set(AUTO_POST_KEY, "true", user=other)
        self.assertFalse(is_auto_post_enabled(self.user))

    def test_failure_never_blocks_sign_in(self):
        AppSettings.set(AUTO_POST_KEY, "true", user=self.user)
        with patch("core.services.budgets.auto_post.RecurringService.process_due", side_effect=RuntimeError("boom")):
            self.assertEqual(auto_post_on_login(self.user), 0)


class AutoPostLoginTests(AutoPostBase):
    def test_api_login_posts_only_when_enabled(self):
        res = self.client.post("/api/auth/login/", {"username": "rec_login", "password": PW}, content_type="application/json")
        self.assertEqual(res.json()["recurring_posted"], 0)
        self.assertEqual(self.posted(), 0)
        self.client.logout()
        AppSettings.set(AUTO_POST_KEY, "true", user=self.user)
        res = self.client.post("/api/auth/login/", {"username": "rec_login", "password": PW}, content_type="application/json")
        self.assertEqual(res.json()["recurring_posted"], 1)
        self.assertEqual(self.posted(), 1)

    def test_page_login_posts_when_enabled(self):
        AppSettings.set(AUTO_POST_KEY, "true", user=self.user)
        self.client.post("/accounts/login/", {"username": "rec_login", "password": PW})
        self.assertEqual(self.posted(), 1)

    def test_member_can_toggle_through_settings_api(self):
        self.client.force_login(self.user)
        res = self.client.post("/api/settings/", {"key": AUTO_POST_KEY, "value": "true"}, content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(is_auto_post_enabled(self.user))
        got = self.client.get("/api/settings/").json()["settings"]
        self.assertEqual(got[AUTO_POST_KEY], "true")
