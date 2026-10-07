"""A lapsed trial/subscription must lock the data API (the banner alone used to be cosmetic)."""

import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.authentication.services import AuthWorkflowService
from core.models import Currency, Invoice, Plan, Subscription
from core.services.billing import SubscriptionService

User = get_user_model()
DATA_GETS = ["/api/expenses/", "/api/balance/", "/api/banks/", "/api/fixed-assets/", "/api/dashboard/", "/api/budgets/",
             "/api/salary/", "/api/goals/", "/api/currencies/", "/api/companies/", "/api/reminders/", "/api/gold/"]
ALWAYS_OK = ["/api/billing/status/", "/api/billing/plans/", "/api/auth/me/", "/api/settings/"]


def _is_402(res):
    return res.status_code == 402 and res.json().get("error") == "subscription_required"


class SubscriptionEnforcementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.plan = Plan.objects.create(code="enf_plan", name="Enf", sort_order=1)

    def user(self, name, status=None, trial_end=None, **flags):
        u = User.objects.create_user(username=name, password="pw12345!", **flags)
        if status:
            Subscription.objects.create(owner=u, plan=self.plan, status=status, trial_end=trial_end)
        return u

    def login(self, u):
        self.client.force_login(u)

    # --- lapsed users are locked out -------------------------------------------------------------------------
    def test_expired_trial_blocks_every_data_endpoint(self):
        u = self.user("expired", "trialing", timezone.now() - timedelta(days=1))   # trial ran out, status not flipped yet
        self.login(u)
        for path in DATA_GETS:
            self.assertTrue(_is_402(self.client.get(path)), path)
        res = self.client.post("/api/expenses/", json.dumps({"amount": 1}), content_type="application/json")
        self.assertTrue(_is_402(res))
        self.assertEqual(Subscription.objects.get(owner=u).status, "expired")        # flipped on first check

    def test_expired_canceled_and_unpaid_statuses_are_blocked(self):
        for i, status in enumerate(["expired", "canceled"]):
            u = self.user(f"lapsed_{i}", status)
            self.login(u)
            self.assertTrue(_is_402(self.client.get("/api/balance/")), status)

    def test_lapsed_user_can_still_sign_out_see_plans_and_upgrade(self):
        u = self.user("lapsed_ok", "expired")
        self.login(u)
        for path in ALWAYS_OK:
            self.assertNotEqual(self.client.get(path).status_code, 402, path)
        status = self.client.get("/api/billing/status/").json()
        self.assertFalse(status["subscription"]["has_access"])
        res = self.client.post("/api/billing/upgrade-request/", json.dumps({"plan_id": self.plan.id}), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        self.assertNotEqual(self.client.post("/accounts/logout/").status_code, 402)

    def test_lapsed_user_cannot_write_settings_or_export(self):
        self.login(self.user("lapsed_set", "expired"))
        res = self.client.post("/api/settings/", json.dumps({"active_language": "fr"}), content_type="application/json")
        self.assertTrue(_is_402(res))
        self.assertTrue(_is_402(self.client.get("/api/settings/backup/list/")))

    def test_shell_and_public_pages_stay_reachable(self):
        self.login(self.user("lapsed_shell", "expired"))
        for path in ("/", "/privacy/", "/terms/"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    # --- nobody else is affected -----------------------------------------------------------------------------
    def test_active_and_current_trial_users_are_not_blocked(self):
        for i, (status, end) in enumerate([("active", None), ("trialing", timezone.now() + timedelta(days=3))]):
            self.login(self.user(f"ok_{i}", status, end))
            for path in DATA_GETS[:4]:
                self.assertNotEqual(self.client.get(path).status_code, 402, (status, path))

    def test_user_without_subscription_row_is_not_blocked(self):
        self.login(self.user("unbilled"))
        self.assertFalse(SubscriptionService.is_lapsed(User.objects.get(username="unbilled")))
        self.assertNotEqual(self.client.get("/api/balance/").status_code, 402)

    def test_superuser_and_sysadmin_are_never_blocked_even_if_lapsed(self):
        su = self.user("su", "expired", is_superuser=True, is_staff=True)
        sa = self.user("sa", "expired")
        profile = AuthWorkflowService.get_profile(sa)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        for u in (su, sa):
            self.login(u)
            self.assertNotEqual(self.client.get("/api/balance/").status_code, 402, u.username)

    def test_upgrading_unlocks_immediately(self):
        u = self.user("upgrader", "expired")
        self.login(u)
        self.assertTrue(_is_402(self.client.get("/api/balance/")))
        Subscription.objects.filter(owner=u).update(status="active", current_period_end=timezone.now() + timedelta(days=30))
        self.assertNotEqual(self.client.get("/api/balance/").status_code, 402)

    def test_anonymous_still_gets_401_not_402(self):
        self.assertEqual(self.client.get("/api/balance/").status_code, 401)

    # --- the "pay to unlock" path: fake checkout is test-mode only ------------------------------------------------
    def _lapsed_with_invoice(self, name):
        u = self.user(name, "expired")
        cur = Currency.objects.filter(owner=None).first() or Currency.objects.create(code="USD", name="US Dollar", symbol="$", owner=None)
        inv = Invoice.objects.create(owner=u, subscription=u.subscription, plan=self.plan, amount=5, currency=cur, status="pending")
        self.login(u)
        return u, inv

    def _fake_complete(self, inv):
        return self.client.post("/api/billing/checkout/fake-complete/", json.dumps({"invoice_id": inv.id}), content_type="application/json")

    def test_lapsed_user_stays_locked_when_a_real_gateway_is_configured(self):
        u, inv = self._lapsed_with_invoice("pay_real")
        with patch("core.services.billing.paymob_gateway.PaymobGateway.any_configured", return_value=True):
            self.assertEqual(self._fake_complete(inv).status_code, 400)       # fake payments refused
        self.assertEqual(Invoice.objects.get(pk=inv.pk).status, "pending")
        self.assertTrue(_is_402(self.client.get("/api/balance/")))            # still locked

    def test_fake_checkout_unlocks_only_in_test_mode_without_a_gateway(self):
        u, inv = self._lapsed_with_invoice("pay_fake")
        with patch("core.services.billing.paymob_gateway.PaymobGateway.any_configured", return_value=False):
            self.assertEqual(self._fake_complete(inv).status_code, 200)
        self.assertNotEqual(self.client.get("/api/balance/").status_code, 402)  # documented test-mode behaviour
