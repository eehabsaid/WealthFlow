import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from core.models import BalanceEntry, Currency, Expense

User = get_user_model()


class ImportViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="import_view_owner", password="pass12345")
        self.client.force_login(self.user)
        self.egp = Currency.objects.create(code="EGP", symbol="EGP", name="Egyptian Pound")
        BalanceEntry.objects.create(
            owner=self.user, title="Cash (EGP)", balance_type=BalanceEntry.BalanceType.CASH,
            bank=None, currency=self.egp, amount=10000,
        )

    def test_requires_authentication(self):
        self.client.logout()
        res = self.client.post("/api/import/preview/")
        self.assertNotEqual(res.status_code, 200)

    def test_preview_missing_file_returns_400(self):
        res = self.client.post("/api/import/preview/")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error_key"], "no_file")

    def test_preview_unsupported_type_returns_400(self):
        f = SimpleUploadedFile("statement.pdf", b"whatever")
        res = self.client.post("/api/import/preview/", {"file": f})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error_key"], "unsupported_file_type")

    def test_preview_valid_csv_returns_rows(self):
        content = b"Date,Amount,Description\n2026-01-05,150.00,Groceries\n"
        f = SimpleUploadedFile("statement.csv", content)
        res = self.client.post("/api/import/preview/", {"file": f})
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload["total_rows"], 1)

    def test_confirm_end_to_end(self):
        rows = [{"Date": "2026-01-05", "Amount": "150.00", "Description": "Groceries"}]
        mapping = {"date": "Date", "amount": "Amount", "description": "Description"}
        res = self.client.post(
            "/api/import/confirm/",
            data=json.dumps({"rows": rows, "mapping": mapping, "currency_id": self.egp.id}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["created_count"], 1)
        self.assertEqual(Expense.objects.filter(owner=self.user).count(), 1)

    def test_confirm_missing_mapping_returns_400(self):
        res = self.client.post(
            "/api/import/confirm/",
            data=json.dumps({"rows": [{"a": 1}], "mapping": {}}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error_key"], "mapping_incomplete")
