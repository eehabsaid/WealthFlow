import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from core.services.import_data.column_mapper import parse_amount_value, parse_date_value, suggest_mapping
from core.services.import_data.parsers import EmptyFileError, UnsupportedFileTypeError, parse_uploaded_file


class CsvParserTest(TestCase):
    def test_parses_headers_and_rows(self):
        content = "Date,Amount,Description\n2026-01-05,150.00,Groceries\n2026-01-06,25.50,Coffee\n"
        f = SimpleUploadedFile("statement.csv", content.encode("utf-8"))
        headers, rows = parse_uploaded_file(f)
        self.assertEqual(headers, ["Date", "Amount", "Description"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["Amount"], "150.00")

    def test_skips_blank_lines(self):
        content = "Date,Amount\n2026-01-01,10\n\n2026-01-02,20\n"
        f = SimpleUploadedFile("s.csv", content.encode("utf-8"))
        headers, rows = parse_uploaded_file(f)
        self.assertEqual(len(rows), 2)

    def test_empty_file_raises(self):
        f = SimpleUploadedFile("s.csv", b"")
        with self.assertRaises(EmptyFileError):
            parse_uploaded_file(f)

    def test_unsupported_extension_raises(self):
        f = SimpleUploadedFile("s.pdf", b"whatever")
        with self.assertRaises(UnsupportedFileTypeError):
            parse_uploaded_file(f)

    def test_arabic_windows_encoding_fallback(self):
        # cp1256 bytes for an Arabic header, undecodable as strict utf-8.
        content = "التاريخ,المبلغ\n2026-01-01,100\n".encode("cp1256")
        f = SimpleUploadedFile("s.csv", content)
        headers, rows = parse_uploaded_file(f)
        self.assertEqual(len(rows), 1)


class ExcelParserTest(TestCase):
    def test_parses_xlsx(self):
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.append(["Date", "Amount", "Description"])
        ws.append(["2026-02-01", 99.5, "Fuel"])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        f = SimpleUploadedFile(
            "statement.xlsx", buf.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        headers, rows = parse_uploaded_file(f)
        self.assertEqual(headers, ["Date", "Amount", "Description"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Description"], "Fuel")


class ColumnMapperTest(TestCase):
    def test_suggest_mapping_matches_common_headers(self):
        mapping = suggest_mapping(["Transaction Date", "Debit", "Details", "Category"])
        self.assertEqual(mapping["date"], "Transaction Date")
        self.assertEqual(mapping["amount"], "Debit")
        self.assertEqual(mapping["description"], "Details")
        self.assertEqual(mapping["category"], "Category")

    def test_suggest_mapping_arabic_headers(self):
        mapping = suggest_mapping(["تاريخ", "مبلغ", "بيان"])
        self.assertEqual(mapping["date"], "تاريخ")
        self.assertEqual(mapping["amount"], "مبلغ")
        self.assertEqual(mapping["description"], "بيان")

    def test_parse_date_value_multiple_formats(self):
        self.assertEqual(parse_date_value("2026-01-05").isoformat(), "2026-01-05")
        self.assertEqual(parse_date_value("05/01/2026").isoformat(), "2026-01-05")
        self.assertIsNone(parse_date_value(""))
        self.assertIsNone(parse_date_value("not-a-date"))

    def test_parse_amount_value_handles_commas_and_parentheses(self):
        self.assertEqual(parse_amount_value("1,250.50"), 1250.50)
        self.assertEqual(parse_amount_value("(99.99)"), 99.99)
        self.assertIsNone(parse_amount_value(""))
        self.assertIsNone(parse_amount_value("abc"))
