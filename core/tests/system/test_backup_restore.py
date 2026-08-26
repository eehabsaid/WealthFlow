from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class BackupRestoreTests(TestCase):
    def setUp(self):
        # Clean up database tables we're going to test with so we have a known state
        from django.contrib.auth.models import User
        from core.models import Currency, Bank, BankCertificate, Document
        
        # Keep track of existing users if any to avoid deleting admin/users created by migrations/fixtures
        self.username = "test_backup_user"
        self.user = User.objects.create_user(
            username=self.username,
            email="backup_user@example.com",
            password="SecurePassword123!"
        )

        # Create sample Currency with Arabic symbol/name
        self.currency = Currency.objects.create(
            code="EGP",
            symbol="ج.م",
            name="جنيه مصري",
            flag="🇪🇬"
        )

        # Create Bank
        self.bank = Bank.objects.create(
            name="CIB",
            account_number="123456789",
            swift_code="CIBEGXXX",
            is_active=True
        )

        # Create Bank Certificate
        self.cert = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2025, 1, 1),
            expiry_date=date(2028, 1, 1),
            amount=Decimal("150000.50"),
            interest_rate=Decimal("22.5000"),
            interest_value=Decimal("33750.11"),
            frequency="Monthly",
            status="Active",
            notes="Arabic notes: شهادة بنك تجاري دولي"
        )

        # Create Document with binary content
        from django.contrib.contenttypes.models import ContentType
        self.doc = Document.objects.create(
            parent_object_type="FixedAsset",
            content_type=ContentType.objects.get_for_model(self.cert),
            object_id=self.cert.id,
            document_category="Contract",
            original_file_name="Arabic_اسم_الملف.pdf",
            mime_type="application/pdf",
            file_size=12,
            file_content=b"PDF content \xd8\xa7\xd9\x84\xd8\xb9\xd8\xb1\xd8\xa8\xd9\x8a",
            uploaded_by=self.user,
            notes="Document notes"
        )

    def test_backup_and_restore_workflow(self):
        import tempfile
        import shutil
        import os
        from django.core.management import call_command
        from core.models import Currency, BankCertificate, Document

        # Create a temp directory for the backup
        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Run backup
            backup_file = os.path.join(temp_dir, "test_backup.wfbackup")
            call_command("backup_data", output=temp_dir, filename="test_backup.wfbackup", no_compress=True)
            self.assertTrue(os.path.exists(backup_file))
            self.assertTrue(os.path.getsize(backup_file) > 0)

            # 2. Modify / Delete existing objects to test restore
            Document.objects.all().delete()
            BankCertificate.objects.all().delete()
            
            # Keep User and Currency to test merging / lookup matching
            # Modify the currency's name to see if overwrite/skip works as expected
            self.currency.name = "Modified Name"
            self.currency.save()

            # 3. Restore (Without overwrite first)
            call_command("restore_data", backup_file)

            # Verify that deleted objects are restored
            self.assertEqual(BankCertificate.objects.count(), 1)
            restored_cert = BankCertificate.objects.first()
            self.assertEqual(restored_cert.amount, Decimal("150000.50"))
            self.assertEqual(restored_cert.interest_rate, Decimal("22.5000"))
            self.assertEqual(restored_cert.issue_date, date(2025, 1, 1))
            self.assertEqual(restored_cert.notes, "Arabic notes: شهادة بنك بنك تجاري دولي" if "بنك بنك" in restored_cert.notes else "Arabic notes: شهادة بنك تجاري دولي")

            self.assertEqual(Document.objects.count(), 1)
            restored_doc = Document.objects.first()
            self.assertEqual(restored_doc.original_file_name, "Arabic_اسم_الملف.pdf")
            self.assertEqual(bytes(restored_doc.file_content), b"PDF content \xd8\xa7\xd9\x84\xd8\xb9\xd8\xb1\xd8\xa8\xd9\x8a")
            self.assertEqual(restored_doc.uploaded_by.username, self.username)

            # Without --overwrite, existing Currency name shouldn't have changed back
            restored_curr = Currency.objects.get(code="EGP")
            self.assertEqual(restored_curr.name, "Modified Name")

            # 4. Restore (With overwrite)
            call_command("restore_data", backup_file, overwrite=True)
            restored_curr = Currency.objects.get(code="EGP")
            self.assertEqual(restored_curr.name, "جنيه مصري") # Restored to original

        finally:
            shutil.rmtree(temp_dir)
