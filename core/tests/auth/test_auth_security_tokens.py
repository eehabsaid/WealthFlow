import json
import re
import smtplib
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from core.models import AppSettings
from core.services.shared.auth_workflow_service import AuthWorkflowService

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="noreply@example.com")
class AuthSecurityTokensTest(TestCase):
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
