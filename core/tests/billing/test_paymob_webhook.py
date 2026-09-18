"""
Paymob webhook handling tests (PaymobWebhookTestCase group).

Split out of the former monolithic test_checkout_flow.py (200-line rule).
"""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Currency, Invoice, Plan, PlanPrice, Subscription
from core.services.billing.subscription_service import SubscriptionService

User = get_user_model()


class PaymobWebhookTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="webhook_user", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", name="Egyptian Pound")
        self.pro = Plan.objects.create(code="wh_pro", name="Webhook Pro", sort_order=1)
        PlanPrice.objects.create(plan=self.pro, currency=self.egp, amount="250.00")
        SubscriptionService.start_trial(self.user)
        self.invoice = Invoice.objects.create(
            owner=self.user,
            subscription=SubscriptionService.get_subscription(self.user),
            plan=self.pro,
            amount="250.00",
            currency=self.egp,
            status="pending",
        )

    def test_webhook_rejects_missing_or_invalid_hmac(self):
        res = self.client.post(
            "/api/billing/paymob/webhook/?hmac=not-a-real-signature",
            data=json.dumps({"obj": {"success": True, "order": {"merchant_order_id": f"wf-inv-{self.invoice.id}"}}}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 403)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "pending")

    @patch("core.services.billing.paymob_gateway.PaymobGateway.verify_webhook_hmac", return_value=True)
    def test_webhook_marks_invoice_paid_and_activates_plan_on_success(self, _mock_verify):
        res = self.client.post(
            "/api/billing/paymob/webhook/?hmac=whatever",
            data=json.dumps(
                {"obj": {"success": True, "order": {"merchant_order_id": f"wf-inv-{self.invoice.id}"}}}
            ),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "paid")
        subscription = Subscription.objects.get(owner=self.user)
        self.assertEqual(subscription.plan_id, self.pro.id)
        self.assertEqual(subscription.status, "active")

    @patch("core.services.billing.paymob_gateway.PaymobGateway.verify_webhook_hmac", return_value=True)
    def test_webhook_is_idempotent(self, _mock_verify):
        payload = json.dumps(
            {"obj": {"success": True, "order": {"merchant_order_id": f"wf-inv-{self.invoice.id}"}}}
        )
        self.client.post("/api/billing/paymob/webhook/?hmac=whatever", data=payload, content_type="application/json")
        first_paid_at = Invoice.objects.get(id=self.invoice.id).paid_at

        self.client.post("/api/billing/paymob/webhook/?hmac=whatever", data=payload, content_type="application/json")
        second_paid_at = Invoice.objects.get(id=self.invoice.id).paid_at
        self.assertEqual(first_paid_at, second_paid_at)

    @patch("core.services.billing.paymob_gateway.PaymobGateway.verify_webhook_hmac", return_value=True)
    def test_webhook_marks_invoice_failed_on_unsuccessful_transaction(self, _mock_verify):
        res = self.client.post(
            "/api/billing/paymob/webhook/?hmac=whatever",
            data=json.dumps(
                {"obj": {"success": False, "order": {"merchant_order_id": f"wf-inv-{self.invoice.id}"}}}
            ),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "failed")

    def test_webhook_does_not_require_login(self):
        """Paymob calls this server-to-server with no session."""
        res = self.client.post(
            "/api/billing/paymob/webhook/?hmac=bad",
            data=json.dumps({"obj": {}}),
            content_type="application/json",
        )
        self.assertNotEqual(res.status_code, 401)
