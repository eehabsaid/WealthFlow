import re
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from core.models import AppSettings, AuthAuditLog, AuthToken
from core.services.shared.auth_workflow_service import AuthWorkflowService

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
