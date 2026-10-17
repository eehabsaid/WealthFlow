"""Refunds through the gateway that took the payment (Stripe, Paymob). All HTTP mocked."""

from unittest.mock import patch

from django.test import override_settings

from core.models import Invoice
from core.services.billing import CheckoutService
from core.services.billing.paymob_gateway import PaymobGateway

from .customer_admin_support import CustomerAdminBase
from .stripe_support import configure_stripe

STRIPE_HTTP = "core.services.billing.stripe_gateway._stripe_http"
PAYMOB_HTTP = "core.services.billing.paymob_refund.make_json_http_request"
PAYMOB_CFG = {"base_url": "https://accept.paymob.com/api", "api_key": "k", "hmac_secret": "h"}


class GatewayRefundTests(CustomerAdminBase):
    def paid(self, **fields):
        inv = self._invoice()
        CheckoutService._mark_paid_and_activate(inv)
        Invoice.objects.filter(pk=inv.pk).update(**fields)
        inv.refresh_from_db()
        return inv

    def test_stripe_refund_confirmed_then_recorded(self):
        configure_stripe()
        inv = self.paid(gateway="stripe", gateway_transaction_id="pi_9")
        with patch(STRIPE_HTTP, return_value=({"id": "re_1", "status": "succeeded"}, 200, None)) as http:
            res = self._invoice_act(inv, action="refund", amount="40.50")
        self.assertEqual((res.status_code, res.json()["gateway_refund"]), (200, "gateway"))
        form = http.call_args.args[1]
        self.assertEqual((http.call_args.args[0], form["payment_intent"], form["amount"]), ("/refunds", "pi_9", "4050"))
        inv.refresh_from_db()
        self.assertEqual((inv.status, str(inv.refund_amount)), ("refunded", "40.50"))

    def test_stripe_refund_failure_changes_nothing(self):
        configure_stripe()
        inv = self.paid(gateway="stripe", gateway_transaction_id="pi_9")
        with patch(STRIPE_HTTP, return_value=(None, 400, "HTTP 400: charge_already_refunded")):
            res = self._invoice_act(inv, action="refund")
        self.assertEqual(res.status_code, 502)
        self.assertIn("Nothing was changed", res.json()["message"])
        inv.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual((inv.status, inv.refunded_at, self.sub.status), ("paid", None, "active"))

    def test_record_only_skips_the_gateway(self):
        configure_stripe()
        inv = self.paid(gateway="stripe", gateway_transaction_id="pi_9")
        with patch(STRIPE_HTTP) as http:
            res = self._invoice_act(inv, action="refund", manual=True)
        http.assert_not_called()
        self.assertEqual(res.json()["gateway_refund"], "manual")
        self.assertIn("Stripe dashboard", res.json()["message"])

    def test_configured_gateway_but_no_payment_reference_is_refused(self):
        configure_stripe()
        inv = self.paid(gateway="stripe", gateway_transaction_id="")
        self.assertEqual(self._invoice_act(inv, action="refund").status_code, 502)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "paid")

    @override_settings(BILLING_TEST_MODE=True)
    def test_test_mode_without_gateway_never_calls_out(self):
        inv = self.paid(gateway="stripe", gateway_transaction_id="pi_9")
        with patch(STRIPE_HTTP) as http:
            res = self._invoice_act(inv, action="refund")
        http.assert_not_called()
        self.assertEqual((res.status_code, res.json()["gateway_refund"]), (200, "manual"))

    def test_manual_invoice_has_no_gateway_step(self):
        res = self._invoice_act(self.paid(), action="refund")
        self.assertEqual(res.json()["gateway_refund"], "not_applicable")

    def _paymob(self):
        return (
            patch.object(PaymobGateway, "is_configured", return_value=True),
            patch.object(PaymobGateway, "get_config", return_value=PAYMOB_CFG),
            patch.object(PaymobGateway, "_complete", return_value=True),
            patch.object(PaymobGateway, "_auth_token", return_value="tok"),
        )

    def test_paymob_refund_confirmed_sends_transaction_and_cents(self):
        inv = self.paid(gateway="paymob", gateway_reference="77", gateway_transaction_id="555")
        p = self._paymob()
        with p[0], p[1], p[2], p[3], patch(PAYMOB_HTTP, return_value=({"success": "true", "id": 9}, 200, None)) as http:
            res = self._invoice_act(inv, action="refund", amount="40.50")
        self.assertEqual((res.status_code, res.json()["gateway_refund"]), (200, "gateway"))
        self.assertEqual(http.call_args.kwargs["payload"], {"transaction_id": "555", "amount_cents": 4050})
        self.assertEqual(http.call_args.kwargs["headers"], {"Authorization": "Bearer tok"})

    def test_paymob_refund_not_confirmed_changes_nothing(self):
        inv = self.paid(gateway="paymob", gateway_reference="77", gateway_transaction_id="555")
        p = self._paymob()
        with p[0], p[1], p[2], p[3], patch(PAYMOB_HTTP, return_value=({"success": "false"}, 200, None)):
            res = self._invoice_act(inv, action="refund")
        self.assertEqual(res.status_code, 502)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "paid")

    def test_paymob_webhook_stores_transaction_id_for_later_refund(self):
        inv = self._invoice(gateway_reference="77")
        payload = {"obj": {"id": 555, "success": True, "amount_cents": 10000, "currency": inv.currency.code, "order": {"merchant_order_id": f"wf-inv-{inv.id}"}}}
        CheckoutService.process_webhook(payload)
        inv.refresh_from_db()
        self.assertEqual((inv.status, inv.gateway, inv.gateway_transaction_id), ("paid", "paymob", "555"))
