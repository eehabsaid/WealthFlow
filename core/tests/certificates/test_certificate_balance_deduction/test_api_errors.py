from decimal import Decimal
import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Bank, BalanceEntry, BankCertificate, Currency

User = get_user_model()


class CertificateBalanceDeductionApiErrorTest(TestCase):
    """Confirms the view layer converts the two balance-deduction
    exceptions into clean JSON 400 responses (error_code + error) instead
    of an unhandled 500, so the frontend never receives a raw traceback
    body to display."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser_certapi", password="pass12345")
        self.client.force_login(self.user)
        self.egp = Currency.objects.create(code="EGP", symbol="ج.م", name="Egyptian Pound")
        self.enbd = Bank.objects.create(name="ENBD", owner=self.user)
        self.qnb = Bank.objects.create(name="QNB", owner=self.user)
        self.cash_egp = BalanceEntry.objects.create(
            owner=self.user,
            title="ENBD Bank Account Balance",
            balance_type="cash",
            bank=self.enbd,
            currency=self.egp,
            amount=Decimal("10000.00"),
        )

    def test_post_returns_json_400_when_mapping_missing(self):
        response = self.client.post(
            "/api/bank-certificates/",
            data=json.dumps({
                "bank_id": self.qnb.id,
                "currency_id": self.egp.id,
                "issue_date": "2026-01-01",
                "expiry_date": "2026-07-01",
                "amount": 1000,
                "status": "Active",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error_code"], "certificate_balance_mapping_missing")
        self.assertIn("error", payload)
        self.assertEqual(BankCertificate.objects.count(), 0)

    def test_post_returns_json_400_when_insufficient_balance(self):
        response = self.client.post(
            "/api/bank-certificates/",
            data=json.dumps({
                "bank_id": self.enbd.id,
                "currency_id": self.egp.id,
                "issue_date": "2026-01-01",
                "expiry_date": "2026-07-01",
                "amount": 50000,
                "status": "Active",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error_code"], "certificate_insufficient_balance")
        self.assertEqual(BankCertificate.objects.count(), 0)

    def test_put_returns_json_400_when_insufficient_balance(self):
        cert = BankCertificate.objects.create(
            owner=self.user,
            bank=self.enbd,
            currency=self.egp,
            issue_date="2026-01-01",
            expiry_date="2026-07-01",
            amount=Decimal("5000.00"),
            status="Active",
        )
        response = self.client.put(
            f"/api/bank-certificates/{cert.id}/",
            data=json.dumps({"amount": 50000}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error_code"], "certificate_insufficient_balance")
        cert.refresh_from_db()
        self.assertEqual(cert.amount, Decimal("5000.00"))
