"""Sysadmin customer view: list, suspend/unsuspend, extend trial, change plan, invoice paid/void."""

from datetime import timedelta


from core.models import Subscription
from core.services.billing.checkout_service import CheckoutService

from .customer_admin_support import CustomerAdminBase, User


class CustomerAdminTestCase(CustomerAdminBase):
    def test_endpoints_require_sysadmin(self):
        self.client.force_login(self.user)
        self.assertIn(self.client.get("/api/settings/billing/customers/").status_code, (401, 403))
        self.assertIn(self._customer(action="suspend").status_code, (401, 403))
        self.assertIn(self._invoice_act(self._invoice(), action="void").status_code, (401, 403))

    def test_list_shows_plan_status_trial_period_and_invoices(self):
        self._invoice()
        row = next(c for c in self.client.get("/api/settings/billing/customers/").json()["customers"] if c["user_id"] == self.user.id)
        self.assertEqual(row["subscription"]["plan"]["code"], "basic")
        self.assertEqual(row["subscription"]["status"], "trialing")
        self.assertIsNotNone(row["subscription"]["trial_end"])
        self.assertEqual(row["invoice_count"], 1)
        self.assertEqual(row["invoices"][0]["status"], "pending")
        self.assertNotIn(self.admin.id, [c["user_id"] for c in self.client.get("/api/settings/billing/customers/").json()["customers"]])

    def test_list_search(self):
        res = self.client.get("/api/settings/billing/customers/?q=zzz_nomatch").json()
        self.assertEqual(res["customers"], [])

    def test_suspend_blocks_access_and_unsuspend_restores_trial(self):
        self.assertEqual(self._customer(action="suspend").status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "suspended")
        self.assertFalse(self.sub.has_access())
        self.assertEqual(self._customer(action="unsuspend").status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "trialing")
        self.assertTrue(self.sub.has_access())

    def test_unsuspend_paid_period_restores_active_and_expired_stays_expired(self):
        self.sub.status, self.sub.current_period_end = "suspended", self.now + timedelta(days=5)
        self.sub.save()
        self._customer(action="unsuspend")
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "active")
        self.sub.status, self.sub.current_period_end, self.sub.trial_end = "suspended", self.now - timedelta(days=1), self.now - timedelta(days=9)
        self.sub.save()
        self._customer(action="unsuspend")
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "expired")

    def test_unsuspend_when_not_suspended_is_rejected(self):
        self.assertEqual(self._customer(action="unsuspend").status_code, 400)

    def test_cannot_suspend_superuser_or_self(self):
        other = User.objects.create_superuser(username="ca_root", password="pass12345", email="r@r.com")
        Subscription.objects.create(owner=other, plan=self.basic, status="active")
        res = self._act(f"/api/settings/billing/customers/{other.id}/action/", action="suspend")
        self.assertEqual(res.status_code, 403)

    def test_suspended_user_cannot_checkout_and_payment_does_not_unsuspend(self):
        from core.services.billing.checkout_helpers import CheckoutError

        self._customer(action="suspend")
        with self.assertRaises(CheckoutError):
            CheckoutService.initiate_checkout(self.user, self.pro, self.currency)
        inv = self._invoice()
        CheckoutService._mark_paid_and_activate(inv)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "suspended")

    def test_extend_trial_from_future_and_from_expired(self):
        before = self.sub.trial_end
        self._customer(action="extend_trial", days=7)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.trial_end, before + timedelta(days=7))
        self.sub.status, self.sub.trial_end = "expired", self.now - timedelta(days=2)
        self.sub.save()
        self._customer(action="extend_trial", days=5)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "trialing")
        self.assertTrue(self.sub.has_access())

    def test_extend_trial_validation(self):
        for bad in (0, -3, 366, "x", None):
            self.assertEqual(self._customer(action="extend_trial", days=bad).status_code, 400, bad)
        self.sub.status = "active"
        self.sub.save()
        self.assertEqual(self._customer(action="extend_trial", days=3).status_code, 400)

    def test_change_plan(self):
        self.assertEqual(self._customer(action="change_plan", plan_id=self.pro.id).status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.plan_id, self.pro.id)
        self.assertEqual(self._customer(action="change_plan", plan_id=999999).status_code, 404)
        self.pro.is_active = False
        self.pro.save()
        self.assertEqual(self._customer(action="change_plan", plan_id=self.pro.id).status_code, 404)

    def test_unknown_action_and_unknown_user(self):
        self.assertEqual(self._customer(action="nope").status_code, 400)
        self.assertEqual(self._act("/api/settings/billing/customers/999999/action/", action="suspend").status_code, 404)

    def test_mark_paid_activates_and_cannot_repeat(self):
        inv = self._invoice()
        self.assertEqual(self._invoice_act(inv, action="mark_paid").status_code, 200)
        inv.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual((inv.status, self.sub.status, self.sub.plan_id), ("paid", "active", self.pro.id))
        self.assertEqual(self._invoice_act(inv, action="mark_paid").status_code, 400)

    def test_void_only_unpaid(self):
        inv = self._invoice()
        self.assertEqual(self._invoice_act(inv, action="void").status_code, 200)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "void")
        self.assertEqual(self._invoice_act(self._invoice(status="paid"), action="void").status_code, 400)
