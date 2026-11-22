"""Soft-delete tests: forgotten-password self-service and admin-decision restore."""



from django.core.cache import cache
from django.test import TestCase

from core.models import AppSettings
from core.services.account import is_pending_deletion, restore_user, schedule_deletion
from core.tests.account.support import make_user_with_data
from .account_soft_delete_support import PW, User


import re  # noqa: E402

from django.core import mail  # noqa: E402
from django.test import override_settings  # noqa: E402

from core.services.account import restore_needs_admin  # noqa: E402


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="noreply@example.com")
class ForgottenPasswordSelfServiceTests(TestCase):
    """A user who forgot the password restores the account without an admin: reset by email, then restore."""

    def setUp(self):
        cache.clear()
        AppSettings.set("administrator_notification_email", "owner@example.com")
        AppSettings.set("active_language", "en")
        self.a = make_user_with_data("alice")
        self.a.email = "alice@example.com"
        self.a.save(update_fields=["email"])
        schedule_deletion(self.a)

    def test_reset_by_email_then_restore_with_new_password(self):
        self.client.post("/accounts/forgot-password/", {"email": "alice@example.com", "lang": "en"})
        token = re.search(r"/accounts/reset-password/([^/\s]+)/", mail.outbox[0].body).group(1)
        done = self.client.post(f"/accounts/reset-password/{token}/", {"password": "NewSecure123!", "confirm_password": "NewSecure123!", "lang": "en"})
        self.assertContains(done, "auth_password_reset_success_pending_deletion")
        self.assertContains(done, "/accounts/restore/?username=alice")
        self.assertTrue(is_pending_deletion(User.objects.get(username="alice")))  # the reset alone never restores
        self.assertContains(self.client.post("/accounts/restore/", {"username": "alice", "password": PW}), "auth_restore_invalid")  # old password
        self.assertContains(self.client.post("/accounts/restore/", {"username": "alice", "password": "NewSecure123!"}), "auth_restore_done")
        self.assertTrue(self.client.login(username="alice", password="NewSecure123!"))

    def test_restore_page_links_to_forgot_password(self):
        self.assertContains(self.client.get("/accounts/restore/"), "/accounts/forgot-password/")


class RestoreNeverBypassesAdminDecisionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.a = make_user_with_data("alice")

    def _disable_then_delete(self):
        from core.authentication.services import AuthWorkflowService

        AuthWorkflowService.disable_user(self.a)
        self.a.refresh_from_db()
        schedule_deletion(self.a)

    def test_previously_disabled_account_cannot_self_restore(self):
        self._disable_then_delete()
        self.assertTrue(restore_needs_admin(self.a))
        res = self.client.post("/accounts/restore/", {"username": "alice", "password": PW})
        self.assertContains(res, "auth_restore_needs_admin")
        self.assertTrue(is_pending_deletion(User.objects.get(username="alice")))

    def test_admin_restore_returns_to_previous_disabled_state(self):
        self._disable_then_delete()
        self.assertTrue(restore_user(self.a))
        self.a.refresh_from_db()
        self.assertFalse(self.a.is_active)
        self.assertEqual(self.a.profile.account_status, "disabled")
        self.assertFalse(is_pending_deletion(self.a))

    def test_active_account_still_self_restores(self):
        schedule_deletion(self.a)
        self.assertFalse(restore_needs_admin(self.a))
        self.assertContains(self.client.post("/accounts/restore/", {"username": "alice", "password": PW}), "auth_restore_done")
