"""
Fake-mode checkout flow tests (CheckoutFakeModeTestCase group).

Split out of the former monolithic test_checkout_flow.py (200-line rule).
"""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Currency, Invoice, Plan, PlanPrice, Subscription
from core.services.billing import PaymobGateway
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
