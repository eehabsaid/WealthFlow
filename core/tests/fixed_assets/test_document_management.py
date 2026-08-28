from core.models import BankCertificate
from datetime import date
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from core.models import (
    Bank,
    BalanceEntry,
    Currency,
    FixedAsset,
)

User = get_user_model()


class DocumentManagementApiTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="L", name="Egyptian Pound")
        self.bank = Bank.objects.create(name="QNB")
        # Matching cash balance entry required for certificate saves to
        # succeed (see certificate_balance_deduction_service.py).
        BalanceEntry.objects.create(
            title="QNB Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=self.bank,
            currency=self.currency,
            amount=100000,
        )
        self.asset = FixedAsset.objects.create(
            name="Doc Asset",
            asset_type="Other Assets",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=1000,
            current_market_value=1200,
        )
        self.certificate = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2027, 1, 1),
            amount=5000,
            interest_value=500,
            frequency="Monthly",
            status="Active",
        )

    def test_upload_list_download_replace_and_delete_document(self):
        upload = SimpleUploadedFile(
            "contract.pdf",
            b"test-pdf-content",
            content_type="application/pdf",
        )

        response = self.client.post(
            f"/api/documents/fixed_asset/{self.asset.id}/",
            {
                "file": upload,
                "document_category": "Purchase Contracts",
                "notes": "Initial document",
            },
        )
        self.assertEqual(response.status_code, 201)
        created = response.json()
        doc_id = created["id"]

        list_response = self.client.get(f"/api/documents/fixed_asset/{self.asset.id}/")
        self.assertEqual(list_response.status_code, 200)
        docs = list_response.json().get("documents", [])
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["document_category"], "Purchase Contracts")

        inline_response = self.client.get(f"/api/documents/file/{doc_id}/?disposition=inline")
        self.assertEqual(inline_response.status_code, 200)
        self.assertIn("inline;", inline_response["Content-Disposition"])

        replace = SimpleUploadedFile(
            "contract-new.pdf",
            b"new-pdf-content",
            content_type="application/pdf",
        )
        replace_response = self.client.post(
            f"/api/documents/file/{doc_id}/",
            {
                "file": replace,
            },
        )
        self.assertEqual(replace_response.status_code, 200)
        self.assertEqual(replace_response.json()["original_file_name"], "contract-new.pdf")

        delete_response = self.client.delete(f"/api/documents/file/{doc_id}/")
        self.assertEqual(delete_response.status_code, 200)

        final_list = self.client.get(f"/api/documents/fixed_asset/{self.asset.id}/")
        self.assertEqual(final_list.status_code, 200)
        self.assertEqual(final_list.json().get("documents", []), [])

    def test_document_categories_and_validation(self):
        categories_response = self.client.get("/api/documents/categories/?parent_type=bank_certificate")
        self.assertEqual(categories_response.status_code, 200)
        categories = categories_response.json().get("categories", [])
        self.assertIn("Certificate Documents", categories)

        invalid_upload = SimpleUploadedFile(
            "notes.txt",
            b"invalid-extension",
            content_type="text/plain",
        )
        invalid_response = self.client.post(
            f"/api/documents/bank_certificate/{self.certificate.id}/",
            {
                "file": invalid_upload,
                "document_category": "Certificate Documents",
            },
        )
        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(invalid_response.json().get("error"), "invalid_file_type")
