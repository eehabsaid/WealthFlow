"""Sysadmin refund flow: recorded manually (no Paymob refund API), access revoked only when that invoice granted it."""

from datetime import timedelta
from decimal import Decimal

from core.services.billing.checkout_service import CheckoutService

from .customer_admin_support import CustomerAdminBase


class CustomerRefundTestCase(CustomerAdminBase):
    def test_refund_records_and_revokes_access_when_invoice_granted_it(self):
        inv = self._invoice()
        CheckoutService._mark_paid_and_activate(inv)
        res = self._invoice_act(inv, action="refund", note="requested by customer")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["access_revoked"])
        inv.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertEqual((inv.status, inv.refund_amount, inv.refund_note), ("refunded", Decimal("100.00"), "requested by customer"))
        self.assertIsNotNone(inv.refunded_at)
        self.assertEqual(self.sub.status, "canceled")
        self.assertFalse(self.sub.has_access())

    def test_refund_without_revoke_keeps_access(self):
        inv = self._invoice()
        CheckoutService._mark_paid_and_activate(inv)
        res = self._invoice_act(inv, action="refund", revoke_access=False)
        self.assertFalse(res.json()["access_revoked"])
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "active")

    def test_partial_refund_amount_and_validation(self):
        inv = self._invoice(status="paid")
        for bad in (0, -1, "abc", "100.01"):
            self.assertEqual(self._invoice_act(inv, action="refund", amount=bad).status_code, 400, bad)
        self.assertEqual(self._invoice_act(inv, action="refund", amount="40.50").status_code, 200)
        inv.refresh_from_db()
        self.assertEqual(inv.refund_amount, Decimal("40.50"))

    def test_refund_requires_paid_and_is_not_repeatable(self):
        self.assertEqual(self._invoice_act(self._invoice(), action="refund").status_code, 400)
        inv = self._invoice(status="paid")
        self._invoice_act(inv, action="refund")
        self.assertEqual(self._invoice_act(inv, action="refund").status_code, 400)

    def test_refund_of_old_invoice_does_not_revoke_current_period(self):
        old = self._invoice()
        CheckoutService._mark_paid_and_activate(old)
        newer = self._invoice()
        newer.period_end = self.now + timedelta(days=60)
        newer.save()
        CheckoutService._mark_paid_and_activate(newer)
        res = self._invoice_act(old, action="refund")
        self.assertFalse(res.json()["access_revoked"])
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "active")

    def test_paymob_invoice_refund_is_recorded_manually_and_says_so(self):
        inv = self._invoice(gateway_reference="987654")
        CheckoutService._mark_paid_and_activate(inv)
        data = self._invoice_act(inv, action="refund").json()
        self.assertEqual(data["gateway_refund"], "manual")
        self.assertIn("Paymob dashboard", data["message"])
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.gateway, "paymob")

    def test_late_paymob_success_does_not_reactivate_refunded_or_void_invoice(self):
        for status in ("refunded", "void"):
            inv = self._invoice(status=status)
            self.sub.status = "canceled"
            self.sub.save()
            payload = {"obj": {"success": True, "order": {"merchant_order_id": f"wf-inv-{inv.id}"}}}
            from core.services.billing.checkout_helpers import _MERCHANT_ORDER_PREFIX

            payload["obj"]["order"]["merchant_order_id"] = f"{_MERCHANT_ORDER_PREFIX}{inv.id}"
            CheckoutService.process_webhook(payload)
            inv.refresh_from_db()
            self.sub.refresh_from_db()
            self.assertEqual((inv.status, self.sub.status), (status, "canceled"))
