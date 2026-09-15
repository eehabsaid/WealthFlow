import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Currency, Invoice, Plan, PlanPrice, Subscription
from core.services.billing import CheckoutError, CheckoutService, PaymobGateway
from core.services.billing.subscription_service import SubscriptionService

User = get_user_model()


class CheckoutFakeModeTestCase(TestCase):
    """Paymob isn't configured in these tests (no AppSettings keys set),
    so checkout should always fall back to fake/test mode."""

    def setUp(self):
        self.user = User.objects.create_user(username="checkout_user", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", name="Egyptian Pound")
        self.pro = Plan.objects.create(code="co_pro", name="Checkout Pro", sort_order=1)
        PlanPrice.objects.create(plan=self.pro, currency=self.egp, amount="250.00")
        SubscriptionService.start_trial(self.user)
        self.client.force_login(self.user)

    def test_gateway_reports_not_configured_by_default(self):
        self.assertFalse(PaymobGateway.is_configured())

    def test_checkout_endpoint_returns_fake_mode(self):
        res = self.client.post(
            "/api/billing/checkout/",
            data=json.dumps({"plan_id": self.pro.id, "currency_code": "EGP"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["mode"], "fake")
        self.assertIn("invoice_id", data)
        invoice = Invoice.objects.get(id=data["invoice_id"])
        self.assertEqual(invoice.status, "pending")
        self.assertEqual(invoice.plan_id, self.pro.id)

    def test_checkout_rejects_plan_with_no_price_in_currency(self):
        other_plan = Plan.objects.create(code="co_no_price", name="No Price", sort_order=2)
        res = self.client.post(
            "/api/billing/checkout/",
            data=json.dumps({"plan_id": other_plan.id, "currency_code": "EGP"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_fake_complete_activates_subscription_on_the_purchased_plan(self):
        checkout_res = self.client.post(
            "/api/billing/checkout/",
            data=json.dumps({"plan_id": self.pro.id, "currency_code": "EGP"}),
            content_type="application/json",
        )
        invoice_id = checkout_res.json()["invoice_id"]

        complete_res = self.client.post(
            "/api/billing/checkout/fake-complete/",
            data=json.dumps({"invoice_id": invoice_id}),
            content_type="application/json",
        )
        self.assertEqual(complete_res.status_code, 200)

        invoice = Invoice.objects.get(id=invoice_id)
        self.assertEqual(invoice.status, "paid")
        self.assertIsNotNone(invoice.paid_at)

        subscription = Subscription.objects.get(owner=self.user)
        self.assertEqual(subscription.plan_id, self.pro.id)
        self.assertEqual(subscription.status, "active")

    def test_fake_complete_rejects_already_processed_invoice(self):
        checkout_res = self.client.post(
            "/api/billing/checkout/",
            data=json.dumps({"plan_id": self.pro.id, "currency_code": "EGP"}),
            content_type="application/json",
        )
        invoice_id = checkout_res.json()["invoice_id"]
        self.client.post(
            "/api/billing/checkout/fake-complete/",
            data=json.dumps({"invoice_id": invoice_id}),
            content_type="application/json",
        )
        second_res = self.client.post(
            "/api/billing/checkout/fake-complete/",
            data=json.dumps({"invoice_id": invoice_id}),
            content_type="application/json",
        )
        self.assertEqual(second_res.status_code, 400)

    @patch("core.services.billing.paymob_gateway.PaymobGateway.is_configured", return_value=True)
    def test_fake_complete_disabled_once_gateway_is_configured(self, _mock_configured):
        invoice = Invoice.objects.create(
            owner=self.user,
            subscription=SubscriptionService.get_subscription(self.user),
            plan=self.pro,
            amount="250.00",
            currency=self.egp,
            status="pending",
        )
        res = self.client.post(
            "/api/billing/checkout/fake-complete/",
            data=json.dumps({"invoice_id": invoice.id}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "pending")


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


class CheckoutServiceUnitTestCase(TestCase):
    """Direct service-level tests for logic not easily reached via the
    fake-mode HTTP endpoints above."""

    def setUp(self):
        self.user = User.objects.create_user(username="svc_user", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", name="Egyptian Pound")
        self.plan = Plan.objects.create(code="svc_plan", name="Service Plan", sort_order=1)
        PlanPrice.objects.create(plan=self.plan, currency=self.egp, amount="99.00")

    def test_initiate_checkout_without_subscription_raises(self):
        with self.assertRaises(CheckoutError):
            CheckoutService.initiate_checkout(self.user, self.plan, self.egp)
