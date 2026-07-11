import json
import re
import smtplib
from io import StringIO
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from decimal import Decimal


from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from core.models import (
    AppSettings,
    AuthAuditLog,
    AuthToken,
    AssetInsurance,
    BalanceEntry,
    Bank,
    BankCertificate,
    BankCertificateInterestHistory,
    CertificateStatus,
    Company,
    Currency,
    ExchangeRate,
    Expense,
    ExpenseCategory,
    FixedAsset,
    AssetMortgage,
    AssetRental,
    AssetSale,
    RealEstateDetails,
    ReminderLog,
    ReminderRule,
    SalaryEntry,
    UserProfile,
    VehicleDetails,
)
from core.services.shared.auth_workflow_service import AuthWorkflowService
from core.services.certificate.certificate_automation_service import CertificateAutomationService
from core.services.certificate.certificate_interest_service import CertificateInterestService
from core.services.fixed_assets.property_valuation_service import PropertyValuationService
from core.services.shared.reminder_automation_service import ReminderAutomationService
from core.services.shared.scheduler_service import SchedulerService

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="noreply@example.com")
class AuthOnboardingWorkflowTest(TestCase):
    def setUp(self):
        AppSettings.set("administrator_notification_email", "owner@example.com")
        AppSettings.set("active_language", "en")

    def _extract_token(self, body, route_prefix):
        match = re.search(rf"{re.escape(route_prefix)}([^/\s]+)/", body)
        self.assertIsNotNone(match, body)
        return match.group(1)

    def _extract_token_from_outbox(self, route_prefix):
        for message in mail.outbox:
            if route_prefix in message.body:
                return self._extract_token(message.body, route_prefix)
        self.fail(f"No email found containing route prefix: {route_prefix}")

    def test_registration_creates_inactive_unverified_user_and_sends_verification_email(self):
        response = self.client.post(
            "/accounts/signup/",
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "full_name": "New User",
                "lang": "en",
            },
        )

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username="newuser")
        profile = user.profile
        self.assertFalse(user.is_active)
        self.assertFalse(profile.email_verified)
        self.assertEqual(profile.account_status, "pending_email_verification")
        self.assertEqual(profile.preferred_language, "en")
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(AuthAuditLog.objects.filter(user=user, event_type="registration").count(), 1)

    def test_duplicate_email_does_not_create_second_user(self):
        user = User.objects.create_user(username="existing", email="existing@example.com", password="SecurePass123!", is_active=True)
        profile = AuthWorkflowService.get_profile(user)
        profile.email_verified = True
        profile.account_status = "active"
        profile.save(update_fields=["email_verified", "account_status", "updated_at"])

        response = self.client.post(
            "/accounts/signup/",
            {
                "username": "otheruser",
                "email": "existing@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "lang": "en",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email="existing@example.com").count(), 1)
        self.assertContains(response, "auth_error_email_registered")

    def test_email_verification_marks_verified_and_notifies_admin(self):
        self.client.post(
            "/accounts/signup/",
            {
                "username": "verifyme",
                "email": "verifyme@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "lang": "en",
            },
        )
        token = self._extract_token_from_outbox("/accounts/verify-email/")

        response = self.client.get(f"/accounts/verify-email/{token}/")
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username="verifyme")
        profile = user.profile
        profile.refresh_from_db()
        user.refresh_from_db()
        self.assertTrue(profile.email_verified)
        self.assertEqual(profile.account_status, "pending_admin_approval")
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(mail.outbox[2].to, ["owner@example.com"])
        self.assertEqual(AuthAuditLog.objects.filter(user=user, event_type="email_verified").count(), 1)

    def test_invalid_and_expired_tokens_are_rejected(self):
        user = User.objects.create_user(username="tokenuser", email="tokenuser@example.com", password="SecurePass123!", is_active=False)
        profile = AuthWorkflowService.get_profile(user)
        profile.email_verified = False
        profile.account_status = "pending_email_verification"
        profile.save(update_fields=["email_verified", "account_status", "updated_at"])

        invalid_response = self.client.get("/accounts/verify-email/not-a-valid-token/")
        self.assertContains(invalid_response, "auth_token_invalid")

        raw_token = AuthWorkflowService.create_token(user, "email_verification")
        db_token = AuthToken.objects.get(user=user, purpose="email_verification")
        db_token.expires_at = timezone.now() - timedelta(seconds=1)
        db_token.save(update_fields=["expires_at"])

        expired_response = self.client.get(f"/accounts/verify-email/{raw_token}/")
        self.assertContains(expired_response, "auth_token_expired")

    def test_admin_approval_activates_account(self):
        self.client.post(
            "/accounts/signup/",
            {
                "username": "approveuser",
                "email": "approve@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "lang": "en",
            },
        )
        verify_token = self._extract_token_from_outbox("/accounts/verify-email/")
        self.client.get(f"/accounts/verify-email/{verify_token}/")
        approve_token = self._extract_token_from_outbox("/accounts/admin-approve/")

        response = self.client.get(f"/accounts/admin-approve/{approve_token}/")
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username="approveuser")
        user.refresh_from_db()
        profile = user.profile
        profile.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(profile.account_status, "active")
        self.assertEqual(AuthAuditLog.objects.filter(user=user, event_type="admin_approved").count(), 1)

        login_response = self.client.post("/accounts/login/", {"username": "approveuser", "password": "SecurePass123!", "lang": "en"})
        self.assertEqual(login_response.status_code, 302)

    def test_admin_rejection_blocks_login(self):
        self.client.post(
            "/accounts/signup/",
            {
                "username": "rejectuser",
                "email": "reject@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "lang": "en",
            },
        )
        verify_token = self._extract_token_from_outbox("/accounts/verify-email/")
        self.client.get(f"/accounts/verify-email/{verify_token}/")
        reject_token = self._extract_token_from_outbox("/accounts/admin-reject/")
        self.client.get(f"/accounts/admin-reject/{reject_token}/")

        user = User.objects.get(username="rejectuser")
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertEqual(user.profile.account_status, "rejected")

        login_response = self.client.post("/accounts/login/", {"username": "rejectuser", "password": "SecurePass123!", "lang": "en"})
        self.assertContains(login_response, "auth_status_rejected")

    def test_password_reset_keeps_account_status_and_uses_one_time_token(self):
        user = User.objects.create_user(username="resetuser", email="reset@example.com", password="OldPass123!", is_active=False)
        profile = AuthWorkflowService.get_profile(user)
        profile.email_verified = True
        profile.account_status = "pending_admin_approval"
        profile.save(update_fields=["email_verified", "account_status", "updated_at"])

        request_response = self.client.post("/accounts/forgot-password/", {"email": "reset@example.com", "lang": "en"})
        self.assertEqual(request_response.status_code, 200)
        token = self._extract_token(mail.outbox[0].body, "/accounts/reset-password/")

        reset_response = self.client.post(
            f"/accounts/reset-password/{token}/",
            {"password": "NewSecure123!", "confirm_password": "NewSecure123!", "lang": "en"},
        )
        self.assertEqual(reset_response.status_code, 200)

        user.refresh_from_db()
        profile.refresh_from_db()
        self.assertEqual(profile.account_status, "pending_admin_approval")
        self.assertFalse(user.is_active)
        self.assertFalse(self.client.login(username="resetuser", password="NewSecure123!"))

        reuse_response = self.client.post(
            f"/accounts/reset-password/{token}/",
            {"password": "AnotherPass123!", "confirm_password": "AnotherPass123!", "lang": "en"},
        )
        self.assertContains(reuse_response, "auth_token_used")

    def test_login_restrictions_and_existing_users_continue_working(self):
        existing_user = User.objects.create_user(username="legacy", email="legacy@example.com", password="LegacyPass123!", is_active=True)
        existing_profile = AuthWorkflowService.get_profile(existing_user)
        existing_profile.email_verified = True
        existing_profile.account_status = "active"
        existing_profile.save(update_fields=["email_verified", "account_status", "updated_at"])

        pending_user = User.objects.create_user(username="pending", email="pending@example.com", password="PendingPass123!", is_active=False)
        pending_profile = AuthWorkflowService.get_profile(pending_user)
        pending_profile.email_verified = False
        pending_profile.account_status = "pending_email_verification"
        pending_profile.save(update_fields=["email_verified", "account_status", "updated_at"])

        disabled_user = User.objects.create_user(username="disabled", email="disabled@example.com", password="DisabledPass123!", is_active=True)
        AuthWorkflowService.disable_user(disabled_user)

        pending_response = self.client.post("/accounts/login/", {"username": "pending", "password": "PendingPass123!", "lang": "en"})
        self.assertContains(pending_response, "auth_status_verify_email")

        disabled_response = self.client.post("/accounts/login/", {"username": "disabled", "password": "DisabledPass123!", "lang": "en"})
        self.assertContains(disabled_response, "auth_status_disabled")

        legacy_response = self.client.post("/accounts/login/", {"username": "legacy", "password": "LegacyPass123!", "lang": "en"})
        self.assertEqual(legacy_response.status_code, 302)

    @override_settings(DEBUG=False, EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
    @patch("core.services.shared.auth_workflow_service.EmailMultiAlternatives.send", side_effect=ConnectionRefusedError("smtp down"))
    def test_signup_handles_email_delivery_failure_without_500(self, _mock_send):
        response = self.client.post(
            "/accounts/signup/",
            {
                "username": "mailfail",
                "email": "mailfail@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "lang": "en",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "auth_email_delivery_failed")
        self.assertFalse(User.objects.filter(username="mailfail").exists())

    @override_settings(DEBUG=False, EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
    @patch("core.services.shared.auth_workflow_service.EmailMultiAlternatives.send", side_effect=[1, ConnectionRefusedError("welcome down")])
    def test_signup_succeeds_if_welcome_email_fails_after_verification_sent(self, _mock_send):
        response = self.client.post(
            "/accounts/signup/",
            {
                "username": "verifyonly",
                "email": "verifyonly@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "lang": "en",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "auth_signup_success_verify_email")
        self.assertTrue(User.objects.filter(username="verifyonly").exists())

    @patch("core.services.shared.auth_workflow_service.EmailMultiAlternatives.send", return_value=1)
    def test_smtp_test_endpoint_sends_test_email(self, _mock_send):
        admin = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="AdminPass123!",
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        self.client.force_login(admin)
        AppSettings.set("sender_email", "sender@example.com")
        AppSettings.set("smtp_host", "smtp.example.com")
        AppSettings.set("smtp_port", "587")
        AppSettings.set("smtp_username", "sender@example.com")
        AppSettings.set("smtp_password", "secret")

        response = self.client.post(
            "/api/settings/email-test/",
            data=json.dumps({"to_email": "recipient@example.com"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("message_key"), "smtp_test_success")

    @patch(
        "core.services.shared.auth_workflow_service.EmailMultiAlternatives.send",
        side_effect=smtplib.SMTPAuthenticationError(535, b"5.7.139 basic authentication is disabled"),
    )
    def test_smtp_test_endpoint_maps_basic_auth_disabled_error(self, _mock_send):
        admin = User.objects.create_user(
            username="adminuser2",
            email="admin2@example.com",
            password="AdminPass123!",
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        self.client.force_login(admin)
        AppSettings.set("sender_email", "sender@example.com")
        AppSettings.set("smtp_host", "smtp.office365.com")
        AppSettings.set("smtp_port", "587")
        AppSettings.set("smtp_username", "sender@example.com")
        AppSettings.set("smtp_password", "secret")

        response = self.client.post(
            "/api/settings/email-test/",
            data=json.dumps({"to_email": "recipient@example.com"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body.get("ok"))
        self.assertEqual(body.get("message_key"), "smtp_test_error_basic_auth_disabled")


class ProfileBirthdayUpdateTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profileuser",
            email="profile@example.com",
            password="SecurePass123!",
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_profile_update_sets_birthday(self):
        response = self.client.post(
            "/api/auth/profile/",
            data=json.dumps({"full_name": "Profile User", "birthday": "1992-10-15"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["profile"]["birthday"], "1992-10-15")

        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.birthday, date(1992, 10, 15))

    def test_profile_update_allows_clearing_birthday(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.birthday = date(1990, 1, 1)
        profile.save(update_fields=["birthday", "updated_at"])

        response = self.client.post(
            "/api/auth/profile/",
            data=json.dumps({"birthday": ""}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertIsNone(profile.birthday)

    def test_profile_update_rejects_invalid_birthday_format(self):
        response = self.client.post(
            "/api/auth/profile/",
            data=json.dumps({"birthday": "15-10-1992"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid birthday format", response.json().get("error", ""))

    def test_profile_update_rejects_future_birthday(self):
        future_birthday = (date.today() + timedelta(days=3)).isoformat()
        response = self.client.post(
            "/api/auth/profile/",
            data=json.dumps({"birthday": future_birthday}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("error"), "Birthday cannot be in the future.")


class BalanceRecommendationTranslationsTest(SimpleTestCase):
    def test_recommendation_translation_keys_exist(self):
        base_dir = Path(__file__).resolve().parent.parent
        locale_path = base_dir / "static" / "i18n" / "en.json"

        with locale_path.open(encoding="utf-8") as fh:
            translations = json.load(fh)

        required_keys = [
            "recommend_gold_downtrend",
            "recommend_gold_uptrend",
            "recommend_gold_strong_uptrend",
            "recommend_gold_strong_downtrend",
            "recommend_gold_neutral",
            "recommend_maturity_soon",
            "recommend_maturity_very_soon",
            "recommend_large_maturity_90",
            "recommend_idle_cash",
            "recommend_certificate_concentration",
            "recommend_low_liquidity",
            "recommend_high_cash_position",
            "recommend_high_foreign_currency_exposure",
            "recommend_low_emergency_fund",
            "recommend_excess_cash",
            "recommend_low_certificate_allocation",
            "recommend_asset_allocation_balanced",
            "action_renew_certificate",
            "action_gold_certificate_cash",
            "action_gold_cash",
            "action_gold_certificate",
        ]

        missing = [key for key in required_keys if not translations.get(key)]
        self.assertEqual([], missing, f"Missing translation keys: {missing}")


class CertificateForecastBalanceTest(TestCase):
    def test_forecast_excludes_inactive_certificates_from_balance_metrics(self):
        currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        BankCertificate.objects.create(
            currency=currency,
            issue_date=date(2026, 6, 1),
            expiry_date=date(2026, 8, 31),
            amount=300,
            interest_value=50,
            status="Active",
        )
        BankCertificate.objects.create(
            currency=currency,
            issue_date=date(2026, 6, 1),
            expiry_date=date(2026, 8, 31),
            amount=700,
            interest_value=150,
            status="Inactive",
        )

        response = self.client.get("/api/certificate-forecast/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["certificate_balance"], 300.0)
        self.assertEqual(payload["monthly_certificate_income"], 50.0)


class CertificateReportActiveOnlyTest(TestCase):
    def test_certificate_report_uses_active_certificates_only(self):
        currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        BankCertificate.objects.create(
            currency=currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 6, 1),
            amount=500,
            interest_value=50,
            status="Active",
        )
        BankCertificate.objects.create(
            currency=currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 6, 1),
            amount=300,
            interest_value=30,
            status="Inactive",
        )
        response = self.client.get("/api/reports/certificates/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["summary"]["total_count"], 1)
        self.assertEqual(payload["summary"]["total_amount"], 500.0)
        self.assertEqual(payload["summary"]["total_interest"], 50.0)
        self.assertEqual(payload["summary"]["monthly_interest"], 50.0)

        overdue_buckets = payload["buckets"]["overdue"]
        self.assertEqual(len(overdue_buckets), 1)
        self.assertEqual(overdue_buckets[0]["status"], "Active")


class ExpenseSummaryIncomeTest(TestCase):
    def test_income_summary_uses_previous_month_salary_and_certificate_interest_window(self):
        company = Company.objects.create(name="Acme", display_name="Acme")
        SalaryEntry.objects.create(
            company=company,
            year=2026,
            month="june",
            expected=10000,
            paid=5000,
            bonus=0,
        )
        currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")

        BankCertificate.objects.create(
            currency=currency,
            issue_date=date(2026, 6, 1),
            expiry_date=date(2026, 8, 31),
            amount=1000,
            interest_value=100,
            status="Active",
        )
        BankCertificate.objects.create(
            currency=currency,
            issue_date=date(2026, 6, 1),
            expiry_date=date(2026, 8, 31),
            amount=1000,
            interest_value=200,
            status="Inactive",
        )
        BankCertificate.objects.create(
            currency=currency,
            issue_date=date(2026, 9, 1),
            expiry_date=date(2026, 10, 31),
            amount=1000,
            interest_value=999,
            status="Active",
        )

        response = self.client.get("/api/expenses/summary/?year=2026&month=7")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        income_summary = payload["income_summary"]

        self.assertEqual(income_summary["total_salary"], 5000.0)
        self.assertEqual(income_summary["total_interest"], 300.0)
        self.assertEqual(income_summary["total_income"], 5300.0)


class ExpenseBalanceIntegrationTest(TestCase):
    def setUp(self):
        self.currency_egp = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.bank_cib = Bank.objects.create(name="CIB")
        self.bank_qnb = Bank.objects.create(name="QNB")
        self.category = ExpenseCategory.objects.create(name="Utilities", icon="💡", color_hex="#0d6efd")

        self.cash_entry = BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=self.currency_egp,
            amount=2000,
        )
        self.cib_entry = BalanceEntry.objects.create(
            title="CIB Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=self.bank_cib,
            currency=self.currency_egp,
            amount=10000,
        )
        self.qnb_entry = BalanceEntry.objects.create(
            title="QNB Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=self.bank_qnb,
            currency=self.currency_egp,
            amount=5000,
        )

    def test_create_requires_bank_for_card_or_bank_and_deducts_from_matching_balance(self):
        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 300,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Card",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 500,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Cash",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.cash_entry.refresh_from_db()
        self.assertEqual(float(self.cash_entry.amount), 1500.0)

        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-02",
                    "category_id": self.category.id,
                    "amount": 1200,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Bank",
                    "bank_id": self.bank_cib.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.cib_entry.refresh_from_db()
        self.assertEqual(float(self.cib_entry.amount), 8800.0)

    def test_edit_and_delete_restore_and_apply_correct_balance(self):
        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 1200,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Bank",
                    "bank_id": self.bank_cib.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        expense_id = response.json()["id"]

        response = self.client.put(
            f"/api/expenses/{expense_id}/",
            data=json.dumps(
                {
                    "amount": 300,
                    "payment_method": "Card",
                    "bank_id": self.bank_qnb.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        self.cib_entry.refresh_from_db()
        self.qnb_entry.refresh_from_db()
        self.assertEqual(float(self.cib_entry.amount), 10000.0)
        self.assertEqual(float(self.qnb_entry.amount), 4700.0)

        response = self.client.delete(f"/api/expenses/{expense_id}/")
        self.assertEqual(response.status_code, 200)
        self.qnb_entry.refresh_from_db()
        self.assertEqual(float(self.qnb_entry.amount), 5000.0)
        self.assertFalse(Expense.objects.filter(pk=expense_id).exists())

    def test_create_expense_rejected_when_balance_would_be_negative(self):
        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 2500,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Cash",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("error"), "insufficient_balance")
        self.cash_entry.refresh_from_db()
        self.assertEqual(float(self.cash_entry.amount), 2000.0)
        self.assertEqual(Expense.objects.count(), 0)

    def test_edit_expense_rejected_when_new_deduction_would_be_negative(self):
        create_response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 200,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Card",
                    "bank_id": self.bank_qnb.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        expense_id = create_response.json()["id"]

        edit_response = self.client.put(
            f"/api/expenses/{expense_id}/",
            data=json.dumps(
                {
                    "amount": 6000,
                    "payment_method": "Card",
                    "bank_id": self.bank_qnb.id,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(edit_response.status_code, 400)
        self.assertEqual(edit_response.json().get("error"), "insufficient_balance")

        self.qnb_entry.refresh_from_db()
        self.assertEqual(float(self.qnb_entry.amount), 4800.0)

        exp = Expense.objects.get(pk=expense_id)
        self.assertEqual(float(exp.amount), 200.0)
        self.assertEqual(exp.bank_id, self.bank_qnb.id)


class CertificateInterestSynchronizationTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.bank = Bank.objects.create(name="QNB")
        self.cash_balance = BalanceEntry.objects.create(
            title="QNB Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=self.bank,
            currency=self.currency,
            amount=1000,
        )

    def test_service_recovers_missed_periods_and_prevents_duplicates(self):
        certificate = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2026, 1, 15),
            expiry_date=date(2026, 12, 31),
            amount=10000,
            interest_value=100,
            frequency="Monthly",
            status="Active",
            last_interest_posted_date=date(2026, 3, 15),
        )

        service = CertificateInterestService()
        result = service.synchronize(today=date(2026, 7, 20))

        self.assertEqual(result.processed_certificates, 1)
        self.assertEqual(result.posted_periods, 4)
        self.assertEqual(float(result.total_interest_posted), 400.0)

        self.cash_balance.refresh_from_db()
        self.assertEqual(float(self.cash_balance.amount), 1400.0)

        certificate.refresh_from_db()
        self.assertEqual(certificate.last_interest_posted_date, date(2026, 7, 15))
        self.assertEqual(
            BankCertificateInterestHistory.objects.filter(certificate=certificate).count(),
            4,
        )

        second = service.synchronize(today=date(2026, 7, 20))
        self.assertEqual(second.processed_certificates, 0)
        self.assertEqual(second.posted_periods, 0)
        self.cash_balance.refresh_from_db()
        self.assertEqual(float(self.cash_balance.amount), 1400.0)

    def test_service_ignores_inactive_or_expired_certificates(self):
        inactive = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 12, 31),
            amount=5000,
            interest_value=50,
            frequency="Monthly",
            status="Closed",
        )
        expired = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2025, 1, 1),
            expiry_date=date(2026, 3, 1),
            amount=5000,
            interest_value=50,
            frequency="Monthly",
            status="ACTIVE",
        )

        result = CertificateInterestService().synchronize(today=date(2026, 7, 20))
        self.assertEqual(result.processed_certificates, 0)
        self.assertEqual(result.posted_periods, 0)
        self.cash_balance.refresh_from_db()
        self.assertEqual(float(self.cash_balance.amount), 1000.0)
        self.assertFalse(BankCertificateInterestHistory.objects.filter(certificate__in=[inactive, expired]).exists())

    def test_balance_view_triggers_interest_sync(self):
        BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 12, 31),
            amount=7000,
            interest_value=75,
            frequency="Quarterly",
            status="active",
            last_interest_posted_date=date(2026, 1, 1),
        )

        with patch("core.services.certificate.certificate_interest_service.timezone.localdate", return_value=date(2026, 7, 3)):
            response = self.client.get("/api/balance/")

        self.assertEqual(response.status_code, 200)
        self.cash_balance.refresh_from_db()
        self.assertEqual(float(self.cash_balance.amount), 1150.0)

    def test_monthly_posts_only_when_eligible_day_is_reached(self):
        certificate = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2025, 1, 2),
            expiry_date=date(2026, 12, 31),
            amount=7000,
            interest_value=100,
            frequency="Monthly",
            status="Active",
            last_interest_posted_date=date(2026, 6, 2),
        )

        result_before = CertificateInterestService().synchronize(today=date(2026, 7, 1))
        self.assertEqual(result_before.posted_periods, 0)
        self.cash_balance.refresh_from_db()
        self.assertEqual(float(self.cash_balance.amount), 1000.0)

        result_on_day = CertificateInterestService().synchronize(today=date(2026, 7, 2))
        self.assertEqual(result_on_day.posted_periods, 1)
        self.cash_balance.refresh_from_db()
        self.assertEqual(float(self.cash_balance.amount), 1100.0)
        certificate.refresh_from_db()
        self.assertEqual(certificate.last_interest_posted_date, date(2026, 7, 2))

    def test_quarterly_never_posts_future_period(self):
        certificate = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2025, 1, 2),
            expiry_date=date(2026, 12, 31),
            amount=7000,
            interest_value=75,
            frequency="Quarterly",
            status="Active",
            last_interest_posted_date=date(2026, 7, 2),
        )

        result_before_oct = CertificateInterestService().synchronize(today=date(2026, 9, 30))
        self.assertEqual(result_before_oct.posted_periods, 0)

        result_on_oct = CertificateInterestService().synchronize(today=date(2026, 10, 2))
        self.assertEqual(result_on_oct.posted_periods, 1)

        self.cash_balance.refresh_from_db()
        self.assertEqual(float(self.cash_balance.amount), 1075.0)
        certificate.refresh_from_db()
        self.assertEqual(certificate.last_interest_posted_date, date(2026, 10, 2))


class NetWorthIntegrationTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="L", name="Egyptian Pound")
        BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.currency,
            amount=1000,
        )

    def test_balance_grand_total_includes_fixed_assets_current_market_value(self):
        FixedAsset.objects.create(
            name="Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2024, 1, 1),
            purchase_price=500000,
            current_market_value=800000,
        )

        response = self.client.get("/api/balance/")
        self.assertEqual(response.status_code, 200)
        summary = response.json().get("summary", {})

        self.assertEqual(summary.get("fixed_assets_total"), 800000.0)
        self.assertEqual(summary.get("grand_total"), 1000.0)
        self.assertEqual(summary.get("net_worth"), 801000.0)
        expected_formula_total = (
            float((summary.get("totals_by_currency") or {}).get("EGP") or 0)
            + float(summary.get("usd_value") or 0)
            + float(summary.get("eur_value") or 0)
            + float(summary.get("sar_value") or 0)
            + float(summary.get("gold_value") or 0)
        )
        self.assertEqual(summary.get("grand_total"), expected_formula_total)


class FinancialIntelligenceCalibrationTest(TestCase):
    def setUp(self):
        self.egp = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.usd = Currency.objects.create(code="USD", symbol="$", name="US Dollar")
        self.gold = Currency.objects.create(code="GOLD", symbol="g", name="Gold")

    def test_liquidity_uses_cash_entries_and_buy_rate_only(self):
        ExchangeRate.objects.create(currency_code="USD", buy_rate=50, sell_rate=55)

        BalanceEntry.objects.create(
            title="Home Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.egp,
            amount=1000,
        )
        BalanceEntry.objects.create(
            title="USD Wallet",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.usd,
            amount=10,
        )
        BalanceEntry.objects.create(
            title="Gold Grams",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.gold,
            amount=5,
        )
        BalanceEntry.objects.create(
            title="Bank Account",
            balance_type=BalanceEntry.BalanceType.BANK,
            currency=self.egp,
            amount=999999,
        )

        response = self.client.get("/api/certificate-forecast/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        # 1000 EGP + (10 USD * 50 buy rate). Gold and BANK rows are excluded.
        self.assertEqual(payload["cash_balance"], 1500.0)

    def test_low_liquidity_recommendation_requires_real_liquidity_pressure(self):
        BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.egp,
            amount=100000,
        )
        Expense.objects.create(
            date=date(2026, 6, 1),
            year=2026,
            month=6,
            amount=1000,
        )

        healthy = self.client.get("/api/certificate-forecast/")
        self.assertEqual(healthy.status_code, 200)
        healthy_recs = healthy.json().get("financial_recommendations") or []
        self.assertNotIn("recommend_low_liquidity", healthy_recs)

        BalanceEntry.objects.all().delete()
        Expense.objects.all().delete()

        BalanceEntry.objects.create(
            title="Small Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.egp,
            amount=1000,
        )
        Expense.objects.create(date=date(2026, 5, 1), year=2026, month=5, amount=20000)
        Expense.objects.create(date=date(2026, 6, 1), year=2026, month=6, amount=18000)
        Expense.objects.create(date=date(2026, 7, 1), year=2026, month=7, amount=22000)

        stressed = self.client.get("/api/certificate-forecast/")
        self.assertEqual(stressed.status_code, 200)
        stressed_recs = stressed.json().get("financial_recommendations") or []
        self.assertIn("recommend_low_liquidity", stressed_recs)

    def test_recommended_action_is_never_empty(self):
        response = self.client.get("/api/certificate-forecast/")
        self.assertEqual(response.status_code, 200)
        action = response.json().get("action_plan") or {}

        self.assertIsInstance(action, dict)
        self.assertTrue(action.get("key"))

    def test_balance_summary_liquid_egp_cash_uses_cash_egp_rows_only(self):
        bank = Bank.objects.create(name="CIB")
        cash_currency = Currency.objects.create(code="cash", symbol="c", name="Cash")

        BalanceEntry.objects.create(
            title="Home EGP Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.egp,
            amount=1000,
        )
        BalanceEntry.objects.create(
            title="Bank EGP Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=bank,
            currency=self.egp,
            amount=2500,
        )
        BalanceEntry.objects.create(
            title="Cash Currency",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=cash_currency,
            amount=9999,
        )
        BalanceEntry.objects.create(
            title="EGP Bank Type",
            balance_type=BalanceEntry.BalanceType.BANK,
            currency=self.egp,
            amount=7777,
        )

        response = self.client.get("/api/balance/")
        self.assertEqual(response.status_code, 200)
        summary = response.json().get("summary") or {}

        self.assertEqual(summary.get("liquid_egp_cash"), 3500.0)


class RentalIncomeSynchronizationTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.asset = FixedAsset.objects.create(
            name="Rental Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=500000,
            current_market_value=600000,
        )

    def test_rental_income_updates_balance_forecast_and_reports_income(self):
        rental = AssetRental.objects.create(
            asset=self.asset,
            monthly_rent=1000,
            occupancy_rate=80,
            tenant_name="Tenant A",
        )

        self.assertFalse(
            BalanceEntry.objects.filter(notes__startswith="wealthflow:rental-income:asset:").exists()
        )

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        balance_payload = balance_response.json()
        self.assertEqual(balance_payload["summary"]["grand_total"], 800.0)

        forecast_response = self.client.get("/api/certificate-forecast/")
        self.assertEqual(forecast_response.status_code, 200)
        forecast_payload = forecast_response.json()
        self.assertEqual(forecast_payload["monthly_rental_income"], 800.0)

        report_response = self.client.get("/api/expenses/summary/?year=2026&month=7")
        self.assertEqual(report_response.status_code, 200)
        report_payload = report_response.json()["income_summary"]
        self.assertEqual(report_payload["total_rental_income"], 800.0)
        self.assertEqual(report_payload["total_income"], 800.0)

        rental.delete()
        self.assertFalse(
            BalanceEntry.objects.filter(notes__startswith="wealthflow:rental-income:asset:").exists()
        )

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.json()["summary"]["grand_total"], 0.0)


class MortgageSynchronizationTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.asset = FixedAsset.objects.create(
            name="Mortgage Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=500000,
            current_market_value=600000,
        )

    def test_mortgage_updates_balance_and_clears_on_delete(self):
        mortgage = AssetMortgage.objects.create(
            asset=self.asset,
            loan_amount=300000,
            remaining_balance=240000,
            monthly_installment=5000,
            interest_rate=8.5,
            start_date=date(2026, 1, 1),
        )

        self.assertFalse(
            BalanceEntry.objects.filter(notes__startswith="wealthflow:mortgage-liability:asset:").exists()
        )

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.json()["summary"]["net_worth"], 360000.0)

        mortgage.remaining_balance = 200000
        mortgage.save()

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.json()["summary"]["net_worth"], 400000.0)

        mortgage.delete()
        self.assertFalse(
            BalanceEntry.objects.filter(notes__startswith="wealthflow:mortgage-liability:asset:").exists()
        )

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.json()["summary"]["net_worth"], 600000.0)


class AssetSaleSynchronizationTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.deposit_balance = BalanceEntry.objects.create(
            title="Deposit",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.currency,
            amount=1000,
        )
        self.asset = FixedAsset.objects.create(
            name="Sold Car",
            asset_type="Vehicles",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=400000,
            current_market_value=450000,
        )

    def test_asset_sale_updates_selected_balance_and_reverses_on_delete(self):
        sale = AssetSale.objects.create(
            asset=self.asset,
            sale_date=date(2026, 7, 1),
            sale_price=300000,
            selling_expenses=5000,
            net_sale_amount=295000,
            deposit_balance=self.deposit_balance,
        )

        self.deposit_balance.refresh_from_db()
        self.assertEqual(float(self.deposit_balance.amount), 296000.0)

        sale.net_sale_amount = 300000
        sale.save()

        self.deposit_balance.refresh_from_db()
        self.assertEqual(float(self.deposit_balance.amount), 301000.0)

        sale.delete()

        self.deposit_balance.refresh_from_db()
        self.assertEqual(float(self.deposit_balance.amount), 1000.0)


class FixedAssetSnapshotTest(TestCase):
    def test_certificate_forecast_exposes_fixed_assets_snapshot(self):
        FixedAsset.objects.create(
            name="Car",
            asset_type="Vehicles",
            status="Owned",
            purchase_date=date(2025, 6, 1),
            purchase_price=300000,
            current_market_value=250000,
        )

        response = self.client.get("/api/certificate-forecast/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertIn("fixed_assets_balance", payload)
        self.assertIn("fixed_assets_snapshot", payload)
        self.assertGreaterEqual(float(payload.get("fixed_assets_balance") or 0), 250000.0)

    def test_fixed_assets_list_returns_portfolio_snapshot(self):
        FixedAsset.objects.create(
            name="Studio",
            asset_type="Other Assets",
            status="Owned",
            purchase_date=date(2025, 1, 1),
            purchase_price=100000,
            current_market_value=120000,
        )

        response = self.client.get("/api/fixed-assets/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertIn("portfolio_snapshot", payload)
        self.assertEqual(payload["portfolio_snapshot"]["total_fixed_assets_value"], 120000.0)


class DocumentManagementApiTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="L", name="Egyptian Pound")
        self.bank = Bank.objects.create(name="QNB")
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


class CertificateAutomationServiceTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.bank = Bank.objects.create(name="QNB")

    def test_close_matured_certificates_uses_closed_lookup_and_skips_non_active(self):
        CertificateStatus.objects.create(name="cLoSeD", is_terminal=True, order=1)

        active_matured = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 7, 1),
            amount=1000,
            interest_value=10,
            status="Active",
        )
        already_closed = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 7, 1),
            amount=1000,
            interest_value=10,
            status="CLOSED",
        )
        inactive_matured = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 7, 1),
            amount=1000,
            interest_value=10,
            status="Renewed",
        )

        result = CertificateAutomationService().close_matured_certificates(today=date(2026, 7, 4))

        active_matured.refresh_from_db()
        already_closed.refresh_from_db()
        inactive_matured.refresh_from_db()

        self.assertEqual(result.closed_certificates, 1)
        self.assertEqual(active_matured.status, "cLoSeD")
        self.assertEqual(already_closed.status, "CLOSED")
        self.assertEqual(inactive_matured.status, "Renewed")


class ReminderAutomationServiceTest(TestCase):
    def setUp(self):
        self.asset = FixedAsset.objects.create(
            name="Test Vehicle",
            asset_type="Vehicles",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=100000,
            current_market_value=90000,
        )
        self.vehicle = VehicleDetails.objects.create(
            asset=self.asset,
            brand="Toyota",
            plate_number="ABC-123",
            license_expiry_date=date(2026, 7, 7),
        )
        self.insurance = AssetInsurance.objects.create(
            asset=self.asset,
            company="Insurer",
            policy_number="P-1",
            expiry_date=date(2026, 7, 9),
            premium=1000,
        )

    def test_service_generates_insurance_and_vehicle_license_reminders_without_duplicates(self):
        insurance_rule = ReminderRule.objects.create(
            name="Insurance expiry",
            rule_type="insurance_expiry",
            days_before=10,
        )
        vehicle_rule = ReminderRule.objects.create(
            name="Vehicle license expiry",
            rule_type="vehicle_license_expiry",
            days_before=10,
        )

        result = ReminderAutomationService().evaluate(today=date(2026, 7, 4))
        self.assertEqual(result.count, 2)
        self.assertEqual(ReminderLog.objects.count(), 2)

        second = ReminderAutomationService().evaluate(today=date(2026, 7, 4))
        self.assertEqual(second.count, 0)
        self.assertEqual(ReminderLog.objects.filter(rule=insurance_rule).count(), 1)
        self.assertEqual(ReminderLog.objects.filter(rule=vehicle_rule).count(), 1)

    def test_reminder_check_view_uses_service_output(self):
        from unittest.mock import patch
        with patch("django.utils.timezone.localdate") as mock_localdate:
            mock_localdate.return_value = date(2026, 7, 4)
            ReminderRule.objects.create(
                name="Vehicle license expiry",
                rule_type="vehicle_license_expiry",
                days_before=10,
            )

            response = self.client.get("/api/reminders/check/")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["reminders"][0]["rule_type"], "vehicle_license_expiry")

    def test_property_tax_reminder_uses_due_date_settings_and_avoids_duplicates(self):
        real_estate_asset = FixedAsset.objects.create(
            name="Taxed Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=300000,
            current_market_value=500000,
        )
        details = RealEstateDetails.objects.create(
            asset=real_estate_asset,
            country="Egypt",
            city="Cairo",
            governorate="Cairo",
            area_m2=85,
        )
        rule = ReminderRule.objects.create(
            name="Property tax",
            rule_type="property_tax_reminder",
            days_before=10,
        )

        AppSettings.set("property_tax_due_month", "7")
        AppSettings.set("property_tax_due_day", "10")
        AppSettings.set("property_tax_countries", "[\"Egypt\"]")

        first = ReminderAutomationService().evaluate(today=date(2026, 7, 4))
        self.assertEqual(first.count, 1)
        self.assertEqual(first.reminders[0]["rule_type"], "property_tax_reminder")
        self.assertEqual(first.reminders[0]["related_id"], details.id)
        self.assertEqual(first.reminders[0]["days_left"], 6)

        second = ReminderAutomationService().evaluate(today=date(2026, 7, 4))
        self.assertEqual(second.count, 0)
        self.assertEqual(
            ReminderLog.objects.filter(
                rule=rule,
                related_model="RealEstateDetails",
                related_id=details.id,
            ).count(),
            1,
        )


class PropertyValuationServiceTest(TestCase):
    def setUp(self):
        self.asset = FixedAsset.objects.create(
            name="Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=500000,
            current_market_value=600000,
        )
        self.details = RealEstateDetails.objects.create(
            asset=self.asset,
            city="Cairo",
            governorate="Cairo",
            area_m2=100,
        )

    def test_refresh_asset_updates_from_configured_provider(self):
        AppSettings.set(
            "property_valuation_rate_map",
            json.dumps({"by_city": {"Cairo": 42000}}),
        )

        updated, provider_name = PropertyValuationService().refresh_asset(self.asset, today=date(2026, 7, 4))

        self.asset.refresh_from_db()
        self.details.refresh_from_db()

        self.assertTrue(updated)
        self.assertEqual(provider_name, "configured_market_rate")
        self.assertEqual(float(self.asset.current_market_value), 4200000.0)
        self.assertEqual(float(self.details.last_estimated_market_price), 4200000.0)
        self.assertEqual(self.details.valuation_provider, "configured_market_rate")

    def test_refresh_asset_preserves_manual_value_when_unavailable(self):
        updated, provider_name = PropertyValuationService().refresh_asset(self.asset, today=date(2026, 7, 4))

        self.asset.refresh_from_db()
        self.details.refresh_from_db()

        self.assertFalse(updated)
        self.assertIsNone(provider_name)
        self.assertEqual(float(self.asset.current_market_value), 600000.0)
        self.assertEqual(self.details.valuation_provider, "")

    def test_manual_refresh_endpoint_updates_asset(self):
        AppSettings.set(
            "property_valuation_rate_map",
            json.dumps({"by_governorate": {"Cairo": 40000}}),
        )

        response = self.client.post(f"/api/fixed-assets/{self.asset.id}/valuation/refresh/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["updated"])
        self.assertEqual(payload["provider"], "configured_market_rate")

    @patch("core.integrations.property_valuation_api.request.urlopen")
    def test_refresh_asset_uses_external_provider_when_enabled(self, mock_urlopen):
        AppSettings.set("property_valuation_external_enabled", "true")
        AppSettings.set(
            "property_valuation_external_url",
            "https://example.com/valuation?city={city}&area={area_m2}",
        )
        AppSettings.set("property_valuation_external_result_path", "estimated_price")

        response = MagicMock()
        response.read.return_value = b'{"estimated_price": 5100000}'
        mock_urlopen.return_value.__enter__.return_value = response

        updated, provider_name = PropertyValuationService().refresh_asset(
            self.asset,
            today=date(2026, 7, 4),
        )

        self.asset.refresh_from_db()
        self.details.refresh_from_db()

        self.assertTrue(updated)
        self.assertEqual(provider_name, "external_api")
        self.assertEqual(float(self.asset.current_market_value), 5100000.0)
        self.assertEqual(self.details.valuation_provider, "external_api")


class SchedulerAutomationCommandTest(TestCase):
    def test_scheduler_lists_expected_jobs(self):
        jobs = {item["job_id"] for item in SchedulerService().list_jobs()}
        self.assertEqual(
            jobs,
            {
                "reminders",
                "certificate_maturity",
                "certificate_interest",
                "exchange_rates",
                "gold_prices",
                "property_valuation",
            },
        )

    @patch("core.services.shared.scheduler_service.PropertyValuationService.refresh_all")
    @patch("core.services.shared.scheduler_service.GoldValuationService.refresh_latest_prices")
    @patch("core.services.shared.scheduler_service.ExchangeRateService.refresh_latest_rates")
    @patch("core.services.shared.scheduler_service.CertificateInterestService.synchronize")
    @patch("core.services.shared.scheduler_service.CertificateAutomationService.close_matured_certificates")
    @patch("core.services.shared.scheduler_service.ReminderAutomationService.evaluate")
    def test_run_automation_command_executes_registered_jobs(
        self,
        mock_reminders,
        mock_cert_maturity,
        mock_cert_interest,
        mock_rates,
        mock_gold,
        mock_property,
    ):
        class ResultWrapper:
            def __init__(self, payload):
                self.payload = payload

            def to_dict(self):
                return self.payload

        mock_reminders.return_value = ResultWrapper({"count": 1})
        mock_cert_maturity.return_value = ResultWrapper({"closed_certificates": 1})
        mock_cert_interest.return_value = ResultWrapper({"posted_periods": 0})
        mock_rates.return_value = ResultWrapper({"saved": 18})
        mock_gold.return_value = ResultWrapper({"saved": 1})
        mock_property.return_value = ResultWrapper({"updated_assets": 0})

        output = StringIO()
        call_command("run_automation", "--today", "2026-07-04", stdout=output)
        payload = json.loads(output.getvalue())

        self.assertEqual(len(payload), 6)
        self.assertTrue(all(item["success"] for item in payload))


class PayrollAutomationTest(TestCase):
    def setUp(self):
        from core.models import Currency, Bank, Company
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", flag="🇺🇸")
        self.bank = Bank.objects.create(name="Chase Bank", account_number="1234", card_id="5678", swift_code="CHAS")
        self.company = Company.objects.create(
            name="Test Company",
            display_name="Test Company Disp",
            is_active=True,
            current_salary_amount=5000,
            current_salary_currency=self.currency,
            payment_day=25,
            default_bank=self.bank,
        )

    def test_company_to_dict_includes_payroll_fields(self):
        d = self.company.to_dict()
        self.assertEqual(d["current_salary_amount"], 5000.0)
        self.assertEqual(d["current_salary_currency"], "USD")
        self.assertEqual(d["default_bank"], "Chase Bank")

    def test_generate_current_salary_creates_entries(self):
        response = self.client.post("/api/salary/generate-current/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["created"], 1)
        self.assertEqual(data["skipped"], 0)
        
        # Second run should skip
        response = self.client.post("/api/salary/generate-current/")
        self.assertEqual(response.json()["created"], 0)
        self.assertEqual(response.json()["skipped"], 1)

    def test_mark_salary_paid_and_reverse(self):
        from core.models import SalaryEntry, BalanceEntry
        from decimal import Decimal
        
        # Generate entry
        self.client.post("/api/salary/generate-current/")
        entry = SalaryEntry.objects.get(company=self.company)
        self.assertEqual(entry.paid, 0)
        
        # Mark paid
        response = self.client.post(f"/api/salary/{entry.id}/mark-paid/", data=json.dumps({"mark_paid": True}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.paid, 5000.0)
        
        # Check bank balance
        bal = BalanceEntry.objects.get(bank=self.bank, balance_type=BalanceEntry.BalanceType.CASH)
        self.assertEqual(bal.amount, Decimal("5000.00"))
        
        # Reverse payment
        response = self.client.post(f"/api/salary/{entry.id}/mark-paid/", data=json.dumps({"mark_paid": False}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.paid, 0)
        
        # Check bank balance reversed
        bal.refresh_from_db()
        self.assertEqual(bal.amount, Decimal("0.00"))

    def test_company_post_and_put_payroll_fields(self):
        # Test POST creation
        post_data = {
            "name": "New Company API",
            "display_name": "New Company API Disp",
            "group_name": "API Group",
            "color_hex": "#ff0000",
            "is_active": True,
            "order": 5,
            "current_salary_amount": 4200.0,
            "current_salary_currency_id": self.currency.id,
            "payment_day": 20,
            "default_bank_id": self.bank.id,
            "per_diem_amount": 150.0,
            "per_diem_currency_id": self.currency.id,
            "bonus_amount": 500.0,
            "payroll_notes": "Added via POST API",
        }
        response = self.client.post("/api/companies/", data=json.dumps(post_data), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        res_data = response.json()
        new_company_id = res_data["id"]
        self.assertEqual(res_data["current_salary_amount"], 4200.0)
        self.assertEqual(res_data["payment_day"], 20)
        self.assertEqual(res_data["payroll_notes"], "Added via POST API")

        # Test PUT update
        put_data = {
            "current_salary_amount": 4800.0,
            "payment_day": 18,
            "payroll_notes": "Updated via PUT API",
        }
        response = self.client.put(f"/api/companies/{new_company_id}/", data=json.dumps(put_data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data["current_salary_amount"], 4800.0)
        self.assertEqual(res_data["payment_day"], 18)
        self.assertEqual(res_data["payroll_notes"], "Updated via PUT API")

    def test_salary_paid_amount_update_adjusts_balance(self):
        from core.models import SalaryEntry, BalanceEntry
        from decimal import Decimal
        # Generate entry
        self.client.post("/api/salary/generate-current/")
        entry = SalaryEntry.objects.get(company=self.company)
        
        # Mark paid
        self.client.post(f"/api/salary/{entry.id}/mark-paid/", data=json.dumps({"mark_paid": True}), content_type="application/json")
        bal = BalanceEntry.objects.get(bank=self.bank, balance_type=BalanceEntry.BalanceType.CASH)
        self.assertEqual(bal.amount, Decimal("5000.00"))

        # Update paid from 5000 to 6000
        put_data = {
            "paid": 6000.0,
        }
        response = self.client.put(f"/api/salary/{entry.id}/", data=json.dumps(put_data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        
        # Check bank balance adjusted by diff (+1000)
        bal.refresh_from_db()
        self.assertEqual(bal.amount, Decimal("6000.00"))

        # Update paid from 6000 to 4500
        put_data = {
            "paid": 4500.0,
        }
        response = self.client.put(f"/api/salary/{entry.id}/", data=json.dumps(put_data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        
        # Check bank balance adjusted by diff (-1500)
        bal.refresh_from_db()
        self.assertEqual(bal.amount, Decimal("4500.00"))

    def test_salary_deletion_reverses_balance(self):
        from core.models import SalaryEntry, BalanceEntry
        from decimal import Decimal
        # Generate entry
        self.client.post("/api/salary/generate-current/")
        entry = SalaryEntry.objects.get(company=self.company)
        
        # Mark paid (5000)
        self.client.post(f"/api/salary/{entry.id}/mark-paid/", data=json.dumps({"mark_paid": True}), content_type="application/json")
        bal = BalanceEntry.objects.get(bank=self.bank, balance_type=BalanceEntry.BalanceType.CASH)
        self.assertEqual(bal.amount, Decimal("5000.00"))

        # Delete the entry
        response = self.client.delete(f"/api/salary/{entry.id}/")
        self.assertEqual(response.status_code, 200)

        # Check bank balance is fully reversed (5000 - 5000 = 0)
        bal.refresh_from_db()
        self.assertEqual(bal.amount, Decimal("0.00"))


class PerDiemServiceTest(TestCase):
    def setUp(self):
        from core.models import Currency, Bank, Company, ExchangeRate
        from decimal import Decimal
        self.currency_usd, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$", "flag": "🇺🇸", "order": 1})
        self.currency_egp, _ = Currency.objects.get_or_create(code="EGP", defaults={"name": "Egyptian Pound", "symbol": "EGP", "flag": "🇪🇬", "order": 2})
        
        self.bank, _ = Bank.objects.get_or_create(name="Chase Bank", defaults={"account_number": "1234", "card_id": "5678", "swift_code": "CHAS"})
        self.company, _ = Company.objects.get_or_create(
            name="Giza Systems",
            defaults={
                "display_name": "Giza Systems Disp",
                "is_active": True,
            }
        )
        
        # Add exchange rate for USD
        ExchangeRate.objects.create(
            currency_code="USD",
            currency_name="US Dollar",
            buy_rate=Decimal("50.000000"),
            sell_rate=Decimal("50.500000"),
            mid_rate=Decimal("50.250000"),
        )

    def test_create_per_diem_converts_amount_and_updates_balance(self):
        from core.models import PerDiem, BalanceEntry
        post_data = {
            "company_id": self.company.id,
            "year": 2026,
            "date": "2026-07-08",
            "currency_id": self.currency_usd.id,
            "amount": 100.0,
            "bank_id": self.bank.id,
            "notes": "Testing creation",
        }
        
        response = self.client.post("/api/per-diems/", data=json.dumps(post_data), content_type="application/json")
        if response.status_code != 201:
            print("ERROR RESP:", response.content)
        self.assertEqual(response.status_code, 201)
        
        # Verify db record
        pd = PerDiem.objects.get(id=response.json()["id"])
        self.assertEqual(pd.amount, Decimal("100.00"))
        self.assertEqual(pd.amount_egp, Decimal("5000.00")) # 100 * 50
        
        # Verify balance entry
        bal = BalanceEntry.objects.get(bank=self.bank, currency=self.currency_usd, balance_type="cash")
        self.assertEqual(bal.amount, Decimal("100.00"))

    def test_update_per_diem_adjusts_or_reverses_balance(self):
        from core.models import PerDiem, BalanceEntry
        
        # Create first
        post_data = {
            "company_id": self.company.id,
            "year": 2026,
            "date": "2026-07-08",
            "currency_id": self.currency_usd.id,
            "amount": 100.0,
            "bank_id": self.bank.id,
            "notes": "Testing creation",
        }
        response = self.client.post("/api/per-diems/", data=json.dumps(post_data), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        pd_id = response.json()["id"]
        
        # Update bank to Cash (None) and amount to 150
        put_data = {
            "amount": 150.0,
            "bank_id": None,
        }
        response = self.client.put(f"/api/per-diems/{pd_id}/", data=json.dumps(put_data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        
        # Check database updated
        pd = PerDiem.objects.get(id=pd_id)
        self.assertEqual(pd.amount, Decimal("150.00"))
        self.assertEqual(pd.amount_egp, Decimal("7500.00"))
        self.assertIsNone(pd.bank)
        
        # Verify old balance entry reversed (Chase / USD amount should be 0)
        bal_old = BalanceEntry.objects.get(bank=self.bank, currency=self.currency_usd, balance_type="cash")
        self.assertEqual(bal_old.amount, Decimal("0.00"))
        
        # Verify new balance entry created (Cash (None) / USD amount should be 150)
        bal_new = BalanceEntry.objects.get(bank=None, currency=self.currency_usd, balance_type="cash")
        self.assertEqual(bal_new.amount, Decimal("150.00"))

    def test_delete_per_diem_reverses_balance_and_deletes_record(self):
        from core.models import PerDiem, BalanceEntry
        
        # Create first
        post_data = {
            "company_id": self.company.id,
            "year": 2026,
            "date": "2026-07-08",
            "currency_id": self.currency_usd.id,
            "amount": 100.0,
            "bank_id": self.bank.id,
        }
        response = self.client.post("/api/per-diems/", data=json.dumps(post_data), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        pd_id = response.json()["id"]
        
        # Verify balance entry exists with 100
        bal = BalanceEntry.objects.get(bank=self.bank, currency=self.currency_usd, balance_type="cash")
        self.assertEqual(bal.amount, Decimal("100.00"))
        
        # Delete
        response = self.client.delete(f"/api/per-diems/{pd_id}/")
        self.assertEqual(response.status_code, 200)
        
        # Verify deleted from db
        self.assertFalse(PerDiem.objects.filter(id=pd_id).exists())
        
        # Verify balance entry reversed (0.00)
        bal.refresh_from_db()
        self.assertEqual(bal.amount, Decimal("0.00"))

    def test_get_single_per_diem(self):
        # Create first
        post_data = {
            "company_id": self.company.id,
            "year": 2026,
            "date": "2026-07-08",
            "currency_id": self.currency_usd.id,
            "amount": 120.0,
            "bank_id": self.bank.id,
        }
        response = self.client.post("/api/per-diems/", data=json.dumps(post_data), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        pd_id = response.json()["id"]

        # Fetch detail
        response = self.client.get(f"/api/per-diems/{pd_id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["amount"], 120.0)
        self.assertEqual(data["currency_code"], "USD")

    def test_currency_filtering_only_shows_balance_currencies(self):
        from core.models import BalanceEntry
        from decimal import Decimal
        
        # Initially no balance entries, so currencies endpoint should return empty list
        response = self.client.get("/api/per-diems/currencies/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["currencies"]), 0)
        
        # Create a BalanceEntry for USD
        BalanceEntry.objects.create(
            title="My Balance",
            balance_type="cash",
            bank=self.bank,
            currency=self.currency_usd,
            amount=Decimal("1000.00")
        )
        
        # Now USD should show up
        response = self.client.get("/api/per-diems/currencies/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["currencies"]), 1)
        self.assertEqual(response.json()["currencies"][0]["code"], "USD")



