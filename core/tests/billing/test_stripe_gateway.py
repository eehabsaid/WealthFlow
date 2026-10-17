"""Stripe gateway: configuration, checkout, signed webhook, selection. No real keys."""

import json
from unittest.mock import patch

from django.test import override_settings

from core.models import AppSettings
from core.services.billing import CheckoutError, CheckoutService
from core.services.billing.gateways import any_gateway_configured, select_gateway
from core.services.billing.stripe_gateway import StripeGateway, minor_units

from .stripe_support import StripeBase, configure_stripe, session_event, sign

HTTP = "core.services.billing.stripe_gateway._stripe_http"


class StripeGatewayTests(StripeBase):
    def test_not_configured_until_both_secrets_saved(self):
        self.assertFalse(StripeGateway.is_configured())
        configure_stripe()
        self.assertTrue(StripeGateway.is_configured("USD"))
        self.assertFalse(StripeGateway.is_configured("EGP"))
        AppSettings.set("stripe_webhook_secret", "")
        self.assertFalse(StripeGateway.is_configured())

    def test_minor_units_handles_zero_decimal_currencies(self):
        self.assertEqual((minor_units("20.00", "USD"), minor_units("1500", "JPY"), minor_units("0.005", "USD")), (2000, 1500, 1))

    def test_signature_verification(self):
        configure_stripe()
        body = b'{"a":1}'
        self.assertTrue(StripeGateway.verify_webhook(body, sign(body)))
        self.assertFalse(StripeGateway.verify_webhook(body, sign(body, secret="other")))
        self.assertFalse(StripeGateway.verify_webhook(b'{"a":2}', sign(body)))
        self.assertFalse(StripeGateway.verify_webhook(body, sign(body, stamp=1)))  # outside tolerance
        self.assertFalse(StripeGateway.verify_webhook(body, ""))
        self.assertFalse(StripeGateway.verify_webhook(body, "t=abc,v1=zz"))

    def test_checkout_creates_session_and_sends_minor_units(self):
        configure_stripe()
        with patch(HTTP, return_value=({"id": "cs_1", "url": "https://stripe.test/pay"}, 200, None)) as http:
            result = CheckoutService.initiate_checkout(self.user, self.plan, self.usd, return_base="https://wf.test/")
        self.assertEqual((result["mode"], result["redirect_url"]), ("stripe", "https://stripe.test/pay"))
        form = http.call_args.args[1]
        self.assertEqual(form["line_items[0][price_data][unit_amount]"], "2000")
        self.assertEqual(form["line_items[0][price_data][currency]"], "usd")
        inv = self.sub.invoices.get()
        self.assertEqual((inv.gateway, inv.gateway_reference, inv.status), ("stripe", "cs_1", "pending"))
        self.assertEqual(form["client_reference_id"], f"wf-inv-{inv.id}")
        self.assertEqual(form["success_url"], "https://wf.test/#billing-plans")

    def test_checkout_without_return_address_is_refused(self):
        configure_stripe()
        with self.assertRaises(CheckoutError):
            CheckoutService.initiate_checkout(self.user, self.plan, self.usd)

    def test_checkout_failure_marks_invoice_failed_without_leaking_secret(self):
        configure_stripe()
        with patch(HTTP, return_value=(None, 401, "HTTP 401: bad key")):
            with self.assertRaises(CheckoutError) as ctx:
                CheckoutService.initiate_checkout(self.user, self.plan, self.usd, return_base="https://wf.test/")
        self.assertNotIn("sk_test_abc", str(ctx.exception))
        self.assertEqual(self.sub.invoices.get().status, "failed")

    def test_currency_stripe_cannot_charge_is_refused_not_faked(self):
        configure_stripe("EUR")
        with self.assertRaises(CheckoutError):
            CheckoutService.initiate_checkout(self.user, self.plan, self.usd, return_base="https://wf.test/")

    def test_selection_and_fake_mode_switch_off(self):
        self.assertEqual((select_gateway("USD"), any_gateway_configured()), (None, False))
        configure_stripe()
        self.assertEqual((select_gateway("USD"), any_gateway_configured()), ("stripe", True))
        with override_settings(BILLING_TEST_MODE=True):
            res = self.client.post("/api/billing/checkout/fake-complete/", data=json.dumps({"invoice_id": self.invoice().id}), content_type="application/json")
        self.assertEqual(res.status_code, 400)

    def test_webhook_rejects_bad_signature(self):
        configure_stripe()
        inv = self.invoice()
        self.assertEqual(self.post_event(session_event(inv), header="t=1,v1=bad").status_code, 403)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "pending")

    def test_webhook_marks_paid_stores_payment_id_and_activates(self):
        configure_stripe()
        inv = self.invoice(gateway="stripe", gateway_reference="cs_1")
        self.assertEqual(self.post_event(session_event(inv)).status_code, 200)
        inv.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual((inv.status, inv.gateway_transaction_id), ("paid", "pi_123"))
        self.assertEqual((self.sub.status, self.sub.gateway, self.sub.plan_id), ("active", "stripe", self.plan.id))

    def test_webhook_is_idempotent_and_never_revives_refunded_or_void(self):
        configure_stripe()
        for status in ("paid", "refunded", "void"):
            inv = self.invoice(status=status)
            self.post_event(session_event(inv))
            inv.refresh_from_db()
            self.assertEqual((inv.status, inv.gateway_transaction_id), (status, ""))

    def test_webhook_amount_or_currency_mismatch_does_not_activate(self):
        configure_stripe()
        for over in ({"amount_total": 1}, {"currency": "eur"}):
            inv = self.invoice()
            self.post_event(session_event(inv, **over))
            inv.refresh_from_db()
            self.assertEqual(inv.status, "pending", over)

    def test_unpaid_async_and_failed_events(self):
        configure_stripe()
        pending = self.invoice()
        self.post_event(session_event(pending, payment_status="unpaid"))
        pending.refresh_from_db()
        self.assertEqual(pending.status, "pending")
        self.post_event(session_event(pending, kind="checkout.session.expired"))
        pending.refresh_from_db()
        self.assertEqual(pending.status, "failed")

    def test_unrelated_event_and_non_post_are_harmless(self):
        configure_stripe()
        self.assertEqual(self.post_event({"type": "charge.updated", "data": {"object": {}}}).status_code, 200)
        self.assertEqual(self.client.get("/api/billing/stripe/webhook/").status_code, 405)
