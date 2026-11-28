"""Income Analytics exports: valid xlsx/pdf in all 4 languages (test DB)."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Company, Currency, SalaryEntry


def seed(user):
    cur, _ = Currency.objects.get_or_create(owner=user, code="EGP", defaults={"name": "Egyptian Pound"})
    co = Company.objects.create(owner=user, name="Acme", display_name="Acme")
    SalaryEntry.objects.create(
        company=co, year=2025, month="January", paid=Decimal("11000"),
        expected=Decimal("11000"), bonus=Decimal("0"),
    )
    SalaryEntry.objects.create(
        company=co, year=2025, month="February", paid=Decimal("12000"),
        expected=Decimal("12000"), bonus=Decimal("7000"),
    )
    return cur


class IncomeExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="exp_owner", password="pw123456")
        seed(self.user)
        self.client.force_login(self.user)

    def test_xlsx_all_languages(self):
        for lang in ("en", "ar", "fr", "de"):
            r = self.client.get("/api/reports/income/export/", {"format": "xlsx", "lang": lang, "mode": "off", "year": "2025"})
            self.assertEqual(r.status_code, 200, lang)
            self.assertTrue(r["Content-Type"].startswith("application/vnd.openxmlformats"))
            self.assertIn(f"income_2025_{lang}.xlsx", r["Content-Disposition"])
            from io import BytesIO

            from openpyxl import load_workbook

            wb = load_workbook(BytesIO(r.content), read_only=True)
            self.assertEqual(wb.sheetnames, ["Summary", "Breakdown", "Records"])
            ws = wb["Summary"]
            values = [c.value for row in ws.iter_rows(min_row=5, max_row=8, max_col=2) for c in row]
            self.assertIn(30000.0, values)  # 11000 + 12000 salary + 7000 bonus
            wb.close()

    def test_pdf_all_languages(self):
        for lang in ("en", "ar", "fr", "de"):
            r = self.client.get("/api/reports/income/export/", {"format": "pdf", "lang": lang, "mode": "off", "year": "2025"})
            self.assertEqual(r.status_code, 200, lang)
            self.assertEqual(r["Content-Type"], "application/pdf")
            self.assertTrue(r.content.startswith(b"%PDF"))
            self.assertIn(f"income_2025_{lang}.pdf".encode(), r["Content-Disposition"].encode())
            self.assertGreater(len(r.content), 2000)

    def test_xlsx_compare_mode_change_columns(self):
        r = self.client.get(
            "/api/reports/income/export/",
            {"format": "xlsx", "lang": "en", "mode": "yoy", "ya": "2025", "yb": "2025"},
        )
        self.assertEqual(r.status_code, 200)
        from io import BytesIO

        from openpyxl import load_workbook

        wb = load_workbook(BytesIO(r.content), read_only=True)
        ws = wb["Breakdown"]
        header = [c.value for c in next(ws.iter_rows(min_row=5, max_row=5))]
        self.assertIn("Change", header)
        wb.close()

    def test_bad_format_rejected(self):
        r = self.client.get("/api/reports/income/export/", {"format": "txt"})
        self.assertEqual(r.status_code, 400)

    def test_export_requires_auth(self):
        self.client.logout()
        r = self.client.get("/api/reports/income/export/", {"format": "xlsx"})
        self.assertEqual(r.status_code, 401)
