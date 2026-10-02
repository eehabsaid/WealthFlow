from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from core.models import BalanceEntry, Currency, Expense
from core.services.import_data.import_service import ImportService

User = get_user_model()


class ImportServicePreviewTest(TestCase):
    def test_preview_returns_headers_mapping_and_rows(self):
        content = "Date,Amount,Description\n2026-01-05,150.00,Groceries\n"
        f = SimpleUploadedFile("statement.csv", content.encode("utf-8"))
        result = ImportService.preview(f)
        self.assertEqual(result["headers"], ["Date", "Amount", "Description"])
        self.assertEqual(result["total_rows"], 1)
        self.assertEqual(result["suggested_mapping"]["date"], "Date")


class ImportServiceConfirmTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="import_owner", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", symbol="EGP", name="Egyptian Pound")
        BalanceEntry.objects.create(
            owner=self.user, title="Cash (EGP)", balance_type=BalanceEntry.BalanceType.CASH,
            bank=None, currency=self.egp, amount=10000,
        )
        self.mapping = {"date": "Date", "amount": "Amount", "description": "Description", "category": None}

    def test_confirm_creates_expenses(self):
        rows = [
            {"Date": "2026-01-05", "Amount": "150.00", "Description": "Groceries"},
            {"Date": "2026-01-06", "Amount": "25.50", "Description": "Coffee"},
        ]
        result = ImportService.confirm(self.user, rows, self.mapping, currency_id=self.egp.id)
        self.assertEqual(result["created_count"], 2)
        self.assertEqual(Expense.objects.filter(owner=self.user).count(), 2)

    def test_confirm_skips_duplicates(self):
        Expense.objects.create(
            owner=self.user, date=date(2026, 1, 5), year=2026, month=1,
            amount=150, amount_base=150, currency=self.egp, description="Groceries",
        )
        rows = [{"Date": "2026-01-05", "Amount": "150.00", "Description": "Groceries"}]
        result = ImportService.confirm(self.user, rows, self.mapping, currency_id=self.egp.id)
        self.assertEqual(result["created_count"], 0)
        self.assertEqual(result["skipped_duplicate_count"], 1)

    def test_confirm_reports_row_errors_for_bad_data(self):
        rows = [
            {"Date": "not-a-date", "Amount": "150.00", "Description": "Bad date"},
            {"Date": "2026-01-06", "Amount": "", "Description": "Missing amount"},
        ]
        result = ImportService.confirm(self.user, rows, self.mapping, currency_id=self.egp.id)
        self.assertEqual(result["created_count"], 0)
        self.assertEqual(result["error_count"], 2)

    def test_confirm_can_disable_duplicate_skipping(self):
        Expense.objects.create(
            owner=self.user, date=date(2026, 1, 5), year=2026, month=1,
            amount=150, amount_base=150, currency=self.egp, description="Groceries",
        )
        rows = [{"Date": "2026-01-05", "Amount": "150.00", "Description": "Groceries"}]
        result = ImportService.confirm(
            self.user, rows, self.mapping, currency_id=self.egp.id, skip_duplicates=False
        )
        self.assertEqual(result["created_count"], 1)
        self.assertEqual(Expense.objects.filter(owner=self.user).count(), 2)
