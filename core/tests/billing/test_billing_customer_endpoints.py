import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Currency, Plan, PlanPrice
from core.services.billing import SubscriptionService

User = get_user_model()


class BillingCustomerEndpointsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="billing_testuser", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", name="Egyptian Pound")
        self.basic = Plan.objects.create(code="test_basic", name="Test Basic", sort_order=0)
        self.pro = Plan.objects.create(code="test_pro", name="Test Pro", sort_order=1)
        PlanPrice.objects.create(plan=self.basic, currency=self.egp, amount="100.00")
        PlanPrice.objects.create(plan=self.pro, currency=self.egp, amount="250.00")
        self.client.force_login(self.user)

    def test_status_requires_login(self):
        self.client.logout()
        res = self.client.get("/api/billing/status/")
        self.assertEqual(res.status_code, 401)

    def test_status_with_no_subscription(self):
        res = self.client.get("/api/billing/status/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsNone(data["subscription"])
        self.assertIsNone(data["pending_upgrade_request"])
        self.assertFalse(data["has_access"])

    def test_status_with_trialing_subscription(self):
        SubscriptionService.start_trial(self.user)
        res = self.client.get("/api/billing/status/")
        data = res.json()
        self.assertEqual(data["subscription"]["status"], "trialing")
        self.assertTrue(data["subscription"]["has_access"])
        self.assertIsNone(data["pending_upgrade_request"])

    def test_plans_lists_only_active_plans(self):
        Plan.objects.create(code="test_retired", name="Retired", sort_order=2, is_active=False)
        res = self.client.get("/api/billing/plans/")
        codes = [p["code"] for p in res.json()["plans"]]
        self.assertIn("basic", codes)
        self.assertIn("pro", codes)
        self.assertNotIn("retired", codes)

    def test_upgrade_request_creates_pending_request(self):
        res = self.client.post(
            "/api/billing/upgrade-request/",
            data=json.dumps({"plan_id": self.pro.id, "currency_code": "EGP"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()["upgrade_request"]
        self.assertEqual(data["plan_id"], self.pro.id)
        self.assertEqual(data["status"], "pending")

    def test_upgrade_request_is_idempotent(self):
        self.client.post(
            "/api/billing/upgrade-request/",
            data=json.dumps({"plan_id": self.basic.id}),
            content_type="application/json",
        )
        self.client.post(
            "/api/billing/upgrade-request/",
            data=json.dumps({"plan_id": self.pro.id}),
            content_type="application/json",
        )
        self.assertEqual(self.user.upgrade_requests.count(), 1)
        self.assertEqual(self.user.upgrade_requests.first().plan_id, self.pro.id)

    def test_upgrade_request_then_status_reflects_pending(self):
        self.client.post(
            "/api/billing/upgrade-request/",
            data=json.dumps({"plan_id": self.pro.id}),
            content_type="application/json",
        )
        res = self.client.get("/api/billing/status/")
        pending = res.json()["pending_upgrade_request"]
        self.assertIsNotNone(pending)
        self.assertEqual(pending["plan_id"], self.pro.id)

    def test_upgrade_request_rejects_unknown_plan(self):
        res = self.client.post(
            "/api/billing/upgrade-request/",
            data=json.dumps({"plan_id": 999999}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 404)

    def test_upgrade_request_rejects_get(self):
        res = self.client.get("/api/billing/upgrade-request/")
        self.assertEqual(res.status_code, 405)
