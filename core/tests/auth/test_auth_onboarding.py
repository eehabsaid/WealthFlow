import re
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from core.authentication.services.member_role import ensure_member_role
from core.authentication.utils.auth_utils import effective_permission_keys, get_user_allowed_pages
from core.constants.roles import MEMBER_ROLE_KEYS, MEMBER_ROLE_NAME
from core.models import AppSettings, AuthAuditLog, AuthToken, Role, RolePermission, Subscription
from core.services.shared.auth_workflow_service import AuthWorkflowService

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="noreply@example.com")
class AuthOnboardingWorkflowTest(TestCase):
    def setUp(self):
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
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/verify-email/", mail.outbox[0].body)
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
        # No enumeration: identical success message as a fresh signup
        self.assertNotContains(response, "auth_error_email_registered")
        self.assertContains(response, "auth_signup_success_verify_email")
        self.assertFalse(User.objects.filter(username="otheruser").exists())

    def _sign_up(self, username):
        self.client.post(
            "/accounts/signup/",
            {
                "username": username,
                "email": f"{username}@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "lang": "en",
            },
        )

    def test_email_verification_activates_account_without_admin_approval(self):
        self._sign_up("verifyme")
        token = self._extract_token_from_outbox("/accounts/verify-email/")

        response = self.client.get(f"/accounts/verify-email/{token}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "auth_verify_success")

        user = User.objects.get(username="verifyme")
        self.assertTrue(user.is_active)
        self.assertTrue(user.profile.email_verified)
        self.assertEqual(user.profile.account_status, "active")
        self.assertIsNotNone(user.profile.approved_at)
        self.assertEqual(Subscription.objects.get(owner=user).status, "trialing")
        self.assertEqual(AuthAuditLog.objects.filter(user=user, event_type="email_verified").count(), 1)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].to, ["verifyme@example.com"])

    def test_verified_user_gets_member_role_and_can_log_in(self):
        self._sign_up("member")
        token = self._extract_token_from_outbox("/accounts/verify-email/")
        self.client.get(f"/accounts/verify-email/{token}/")

        user = User.objects.get(username="member")
        self.assertEqual(list(user.roles.values_list("role__name", flat=True)), [MEMBER_ROLE_NAME])
        self.assertEqual(effective_permission_keys(user), set(MEMBER_ROLE_KEYS))
        self.assertEqual(get_user_allowed_pages(user)[0], "dashboard")

        login_response = self.client.post("/accounts/login/", {"username": "member", "password": "SecurePass123!", "lang": "en"})
        self.assertEqual(login_response.status_code, 302)

    def test_unverified_user_cannot_log_in(self):
        self._sign_up("unverified")

        login_response = self.client.post("/accounts/login/", {"username": "unverified", "password": "SecurePass123!", "lang": "en"})
        self.assertContains(login_response, "auth_status_verify_email")

    def test_member_role_keys_never_include_platform_admin_tabs(self):
        forbidden = {"settings_users", "settings_billing", "settings_roles", "settings_emailtemplates", "settings_translations", "settings_backuprestore"}
        self.assertFalse(forbidden & set(MEMBER_ROLE_KEYS))

    def test_ensure_member_role_keeps_admin_edits(self):
        role = ensure_member_role(Role, RolePermission)
        RolePermission.objects.filter(role=role, key="settings").delete()

        same_role = ensure_member_role(Role, RolePermission)

        self.assertEqual(same_role.pk, role.pk)
        self.assertFalse(RolePermission.objects.filter(role=role, key="settings").exists())

    def test_check_email_page_and_removed_approval_routes(self):
        self.assertContains(self.client.get("/accounts/check-email/"), "auth_signup_success_verify_email")
        self.assertEqual(self.client.get("/accounts/pending-approval/").status_code, 404)
        self.assertEqual(self.client.get("/accounts/admin-approve/sometoken/").status_code, 404)

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
